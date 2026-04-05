import os
from typing import List, Dict, Any, Optional

from app.services.config import settings
 
_DF = None
_VEC = None
_X = None

def _normalize_columns(cols: List[str]) -> Dict[str, Optional[str]]:
    lower = {c.lower().strip(): c for c in cols}

    def pick(*names: str) -> Optional[str]:
        for n in names:
            if n in lower:
                return lower[n]
        return None

    return {
        "title": pick("title","judul","judul_berita","headline","judul berita"),
        "body": pick("body","content","isi","isi_berita","text","berita","artikel","isi berita"),
        "label": pick("label","kelas","class","target","kategori"),
        "source": pick("source","sumber","origin","portal"),
        "url": pick("url","link","tautan"),
        "date": pick("date","tanggal","published","publish_date","waktu"),
        "text": pick("text","content","isi","berita"),
    }

def _get_dataset_files() -> List[str]:
    env = os.getenv("DATASET_FILES", "app/assets/datasets/dataset_gabungan.csv")
    return [p.strip() for p in env.split(",") if p.strip()]

def load_datasets_on_startup() -> None:
    global _DF, _VEC, _X

    try:
        import pandas as pd
        from sklearn.feature_extraction.text import TfidfVectorizer
    except Exception:
        _DF = None; _VEC = None; _X = None
        return

    files = _get_dataset_files()
    existing = [p for p in files if os.path.exists(p)]
    if not existing:
        _DF = None; _VEC = None; _X = None
        return

    frames = []
    for fp in existing:
        try:
            df = pd.read_csv(fp, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            try:
                df = pd.read_csv(fp, encoding="latin-1", on_bad_lines="skip")
            except Exception:
                continue
        df["_dataset_file"] = os.path.basename(fp)
        frames.append(df)

    if not frames:
        _DF = None; _VEC = None; _X = None
        return

    df = pd.concat(frames, ignore_index=True)

    mapping = _normalize_columns(list(df.columns))
    title_col = mapping["title"]
    body_col  = mapping["body"]
    text_col  = mapping.get("text")
    label_col = mapping["label"]
    source_col = mapping["source"]
    url_col   = mapping["url"]
    date_col  = mapping["date"]

    # Jika tidak ada kolom title terpisah, ekstrak dari text/body
    if title_col:
        df["_title"] = df[title_col].fillna("").astype(str)
    elif text_col:
        # Ekstrak 150 karakter pertama sebagai judul
        df["_title"] = df[text_col].fillna("").astype(str).str[:150].str.strip()
    elif body_col:
        df["_title"] = df[body_col].fillna("").astype(str).str[:150].str.strip()
    else:
        df["_title"] = ""
    
    df["_body"]  = df[body_col].fillna("").astype(str) if body_col else ""
    df["_label"] = df[label_col].fillna("").astype(str) if label_col else ""
    df["_source"] = df[source_col].fillna("").astype(str) if source_col else ""
    df["_url"] = df[url_col].fillna("").astype(str) if url_col else ""
    df["_date"] = df[date_col].fillna("").astype(str) if date_col else ""

    df["_text"] = (df["_title"].str.strip() + "\n" + df["_body"].str.strip()).str.strip()
    df = df[df["_text"].str.len() > 0].copy()

    # Use the same cleaning as model input so similarity aligns
    from app.services.preprocess import clean_text 
    corpus = [clean_text(t) for t in df["_text"].tolist()]

    vec = TfidfVectorizer(
        max_features=100000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )
    X = vec.fit_transform(corpus)

    _DF = df.reset_index(drop=True)
    _VEC = vec
    _X = X

def _ensure_loaded():
    if _DF is None or _VEC is None or _X is None:
        load_datasets_on_startup()

def dataset_stats() -> Dict[str, Any]:
    _ensure_loaded()
    if _DF is None:
        return {"enabled": False, "rows": 0, "files": _get_dataset_files()}
    return {"enabled": True, "rows": int(len(_DF)), "files": _get_dataset_files()}

def search_similar(query_text: str, top_k: int = 5, min_score: float = 0.15) -> List[Dict[str, Any]]:
    _ensure_loaded()
    if _DF is None or not query_text:
        return []

    from app.services.preprocess import clean_text
    q = clean_text(query_text)
    if not q:
        return []

    import numpy as np
    
    # For very short text (< 50 chars), use keyword-based matching
    if len(q) < 50:
        return _keyword_search(q, top_k, min_score)
    
    # For longer text, use TF-IDF
    qv = _VEC.transform([q])
    scores = (_X @ qv.T).toarray().ravel()
    if scores.size == 0 or len(_DF) == 0:
        return []

    # Filter out invalid indices
    top_k = min(top_k, len(_DF))  # Ensure top_k doesn't exceed dataset size
    idxs = np.argsort(scores)[::-1][:max(1, top_k)]
    out: List[Dict[str, Any]] = []
    for i in idxs:
        if i >= len(_DF):  # Safety check
            continue
        sc = float(scores[i])
        if sc < min_score:
            continue
        row = _DF.iloc[int(i)]
        out.append({
            "score": sc,
            "title": str(row.get("_title", ""))[:2000],
            "label_dataset": str(row.get("_label", "")),
            "source": str(row.get("_source", "")),
            "url": str(row.get("_url", "")),
            "date": str(row.get("_date", "")),
            "dataset_file": str(row.get("_dataset_file", "")),
        })
    return out

def _keyword_search(query: str, top_k: int = 5, min_score: float = 0.08) -> List[Dict[str, Any]]:
    """
    Keyword-based search for short text using word overlap + substring matching.
    Better for very short queries where TF-IDF fails.
    """
    if _DF is None:
        return []
    
    # Extract keywords (words >= 3 chars to avoid noise)
    query_words = set(w for w in query.lower().split() if len(w) >= 3)
    if not query_words:
        # Fallback: use all words if all are short
        query_words = set(query.lower().split())
    
    if not query_words:
        return []
    
    query_lower = query.lower()
    
    # Score each document by keyword overlap + substring bonus
    scores = []
    for idx in range(len(_DF)):
        row = _DF.iloc[idx]
        title = str(row.get("_title", "")).lower()
        body = str(row.get("_body", "")).lower()
        text = title + " " + body
        
        # Count matching keywords
        text_words = set(text.split())
        matches = query_words & text_words
        
        if matches or any(qw in title for qw in query_words):
            # Base score: Jaccard similarity
            union_size = len(query_words | text_words)
            if union_size > 0:
                base_score = len(matches) / union_size
            else:
                base_score = 0.0
            
            # Bonus: if multiple query words in title (more relevant)
            title_matches = sum(1 for qw in query_words if qw in title)
            title_bonus = title_matches * 0.05  # +5% per match in title
            
            # Bonus: if query is substring of title
            if query_lower in title:
                substring_bonus = 0.1
            else:
                substring_bonus = 0.0
            
            final_score = base_score + title_bonus + substring_bonus
            scores.append((idx, final_score))
    
    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top_k results above min_score
    out: List[Dict[str, Any]] = []
    for idx, score in scores[:top_k]:
        if score < min_score:
            continue
        row = _DF.iloc[int(idx)]
        out.append({
            "score": float(score),
            "title": str(row.get("_title", ""))[:2000],
            "label_dataset": str(row.get("_label", "")),
            "source": str(row.get("_source", "")),
            "url": str(row.get("_url", "")),
            "date": str(row.get("_date", "")),
            "dataset_file": str(row.get("_dataset_file", "")),
        })
    return out
