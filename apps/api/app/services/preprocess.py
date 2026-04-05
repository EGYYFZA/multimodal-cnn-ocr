import re
from typing import Optional

# ============================================================
# PREPROCESSING YANG SINKRON DENGAN TRAINING (train_mkcnn.py)
# ============================================================

LABEL_CUES = r"""
    hoax|hoaks|penipuan|tipuan|disinformasi|misinformasi|
    palsu|fitnah|provokasi|bohong|tidak\s+benar|
    klarifikasi|cek\s+fakta|factcheck
"""

DOMAIN_TOKENS = r"""
    turnbackhoax|turnbackhoaxid|
    kompas|kompascom|kompas\.com|
    detik|detikcom|liputan6|tribunnews|
    cnnindonesia|tempo|tempo\.co|merdeka|antaranews|komdigi
"""

URL_TOKENS = r"http|https|www|com|id|html|htm|php|bitly|bit\.ly|archive"

def clean_text(text: str) -> str:
    """
    Preprocessing PERSIS seperti train_mkcnn.py.
    PENTING: Jangan ubah urutan atau logika apapun!
    """
    s = str(text)

    # 1. Hapus tag [HOAKS], [SALAH], [PENIPUAN], dll
    s = re.sub(r"\[[^]]*\]", " ", s)

    # 2. Lowercase
    s = s.lower()

    # 3. Hapus URL eksplisit
    s = re.sub(r"http\S+|www\.\S+", " ", s)

    # 4. Hapus domain/url tokens
    s = re.sub(rf"\b({DOMAIN_TOKENS})\b", " ", s, flags=re.IGNORECASE | re.VERBOSE)
    s = re.sub(rf"\b({URL_TOKENS})\b", " ", s, flags=re.IGNORECASE | re.VERBOSE)

    # 5. Hapus kata-kata yang terlalu kuat mengkode label
    s = re.sub(rf"\b({LABEL_CUES})\b", " ", s, flags=re.IGNORECASE | re.VERBOSE)

    # 6. HANYA huruf a-z & spasi (BUANG ANGKA, tanda baca, dll)
    s = re.sub(r"[^a-z\s]", " ", s)

    # 7. Rapikan spasi
    s = re.sub(r"\s+", " ", s).strip()
    
    return s

def merge_inputs(title: str, body: str, ocr_text: str) -> str:
    """
    Gabungkan title, body, dan OCR text dengan SPASI (bukan newline).
    Konsisten dengan project lama: title + ' ' + body + ' ' + ocr
    """
    parts = []
    if title: parts.append(title.strip())
    if body: parts.append(body.strip())
    if ocr_text: parts.append(ocr_text.strip())
    return " ".join([p for p in parts if p])