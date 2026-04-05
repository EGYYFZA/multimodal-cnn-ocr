import os
import io
import re
import shutil
import tempfile
import subprocess
from typing import Tuple, Optional, List

import numpy as np
from PIL import Image, ImageOps

from app.services.config import settings

# =========================================================
#  OCR Service (Robust): preprocess + multi-PSM + CLI fallback
# =========================================================

def _clean_ocr_text(text: str) -> str:
    """
    Bersihkan hasil OCR dengan AGRESIF membuang noise:
    - Prioritaskan kata-kata yang readable (>= 3 huruf berturut)
    - Buang sequences karakter aneh
    - Keep hanya baris yang punya konten meaningful
    """
    if not text:
        return ""
    
    # 1. Hilangkan karakter noise umum dari OCR
    text = re.sub(r'[|_~`^°•●◆◇□■▪▫★☆♦♥♠♣@#$%&*+=<>{}[\]\\]', '', text)
    
    # 2. Hilangkan karakter non-printable
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 3. Normalize quotes dan special chars
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace('»', '').replace('«', '')
    text = text.replace('£', '').replace('€', '')
    
    # 4. Hilangkan sequences noise: 3+ non-alfanumerik berturut
    text = re.sub(r'[^a-zA-Z0-9\s]{3,}', ' ', text)
    
    # 5. Hilangkan karakter aneh terisolasi
    text = re.sub(r'\b[^a-zA-Z0-9\s]{1,2}\b', ' ', text)
    
    # 6. Hilangkan tanda baca berulang
    text = re.sub(r'([.,;:!?])\1{2,}', r'\1', text)
    
    # 7. Extract hanya kata-kata meaningful (>= 2 chars alfanumerik)
    # Ini akan prioritaskan kata-kata penting dan buang noise
    words = []
    for line in text.split('\n'):
        line_words = line.split()
        for word in line_words:
            # Clean word: hapus trailing punctuation
            clean_word = re.sub(r'^[^\w]+|[^\w]+$', '', word)
            
            # Keep jika:
            # - >= 2 karakter alfanumerik
            # - atau angka (tahun, tanggal, dll)
            alphanum_count = sum(c.isalnum() for c in clean_word)
            if alphanum_count >= 2:
                words.append(clean_word)
            elif clean_word.isdigit():  # Keep angka meskipun 1 digit
                words.append(clean_word)
    
    # Join words dengan spasi
    text = ' '.join(words)
    
    # 8. Final cleanup
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces → single
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Space before punctuation
    
    return text.strip()

_CONFIGURED = False
_TESSDATA_DIR: Optional[str] = None


def _resolve_tesseract_exe() -> Optional[str]:
    exe = (settings.tesseract_exe or "").strip()
    if exe and os.path.exists(exe):
        return exe

    if os.name == "nt":
        win_default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(win_default):
            return win_default

    found = shutil.which("tesseract")
    return found


def _resolve_tessdata_dir() -> Optional[str]:
    candidates: List[str] = []

    tdp = (settings.tesseract_data_prefix or os.getenv("TESSDATA_PREFIX", "")).strip()
    if tdp:
        if tdp.lower().endswith("tessdata"):
            candidates.append(tdp)
        else:
            candidates.append(os.path.join(tdp, "tessdata"))

    # Windows umum
    candidates.append(r"C:\Program Files\Tesseract-OCR\tessdata")
    # Linux umum
    candidates.append("/usr/share/tesseract-ocr/4.00/tessdata")
    candidates.append("/usr/share/tesseract-ocr/tessdata")

    for p in candidates:
        if p and os.path.isdir(p):
            try:
                if any(name.endswith(".traineddata") for name in os.listdir(p)):
                    return p
            except Exception:
                pass
    return None


def _configure_tesseract_once() -> None:
    global _CONFIGURED, _TESSDATA_DIR
    if _CONFIGURED:
        return

    _TESSDATA_DIR = _resolve_tessdata_dir()

    # Set env supaya CLI dan pytesseract konsisten
    # (kalau user isi TESSDATA_PREFIX ke induk, tetap oke)
    if settings.tesseract_data_prefix:
        os.environ["TESSDATA_PREFIX"] = settings.tesseract_data_prefix

    try:
        import pytesseract  # noqa
        exe = _resolve_tesseract_exe()
        if exe:
            pytesseract.pytesseract.tesseract_cmd = exe
        # log ringan
        print(f"[OCR] tesseract_exe={exe or '(not found)'} | tessdata_dir={_TESSDATA_DIR or '(auto)'}")
    except Exception as e:
        print(f"[OCR] pytesseract import failed: {e}")

    _CONFIGURED = True


def _cv2_preprocess_variants(img: Image.Image) -> List[Image.Image]:
    """
    OPTIMIZED: Hanya buat 2 varian terbaik:
    - OTSU threshold (bagus untuk teks dengan kontras jelas)
    - Adaptive threshold (bagus untuk gradient/pencahayaan tidak merata)
    
    Kurangi preprocessing yang tidak perlu untuk speed.
    """
    variants: List[Image.Image] = []
    try:
        import cv2
    except Exception:
        return variants

    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    
    # Resize hanya jika terlalu kecil (threshold dikurangi untuk speed)
    if max(w, h) < 1200:
        scale = 1200 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    arr = np.array(img)
    g = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    
    # Bilateral filter - parameter dikurangi untuk speed (5,75,75 dari 7,9,9)
    g = cv2.bilateralFilter(g, 5, 75, 75)

    kernel = np.ones((2, 2), np.uint8)

    # OTSU - metode tercepat dan sering paling akurat
    _, th_otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if float(np.mean(th_otsu)) < 127:
        th_otsu = cv2.bitwise_not(th_otsu)
    th_otsu = cv2.morphologyEx(th_otsu, cv2.MORPH_OPEN, kernel, iterations=1)
    variants.append(Image.fromarray(th_otsu))

    # Adaptive hanya jika memang perlu (skip jika OTSU sudah bagus)
    # Adaptive untuk kasus pencahayaan tidak merata
    th_ad = cv2.adaptiveThreshold(
        g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 5
    )
    if float(np.mean(th_ad)) < 127:
        th_ad = cv2.bitwise_not(th_ad)
    th_ad = cv2.morphologyEx(th_ad, cv2.MORPH_OPEN, kernel, iterations=1)
    variants.append(Image.fromarray(th_ad))

    return variants


def _tesseract_config(psm: int) -> str:
    cfg = f"--oem 3 --psm {psm} --dpi 300 -c preserve_interword_spaces=1"
    if _TESSDATA_DIR:
        cfg += f' --tessdata-dir "{_TESSDATA_DIR}"'
    return cfg


def _get_available_langs() -> List[str]:
    try:
        import pytesseract
        cfg = ""
        if _TESSDATA_DIR:
            cfg = f'--tessdata-dir "{_TESSDATA_DIR}"'
        langs = pytesseract.get_languages(config=cfg)
        return list(langs or [])
    except Exception:
        return []


def _pick_lang_try_order() -> List[str]:
    """
    Urutan coba bahasa.
    Kalau 'ind' tidak ada, fallback ke 'eng' / yang tersedia.
    """
    avail = set(_get_available_langs())
    preferred = ["ind", "ind+eng", "eng"]

    # kalau tidak bisa list, tetap coba default
    if not avail:
        return preferred

    out: List[str] = []
    for l in preferred:
        if "+" in l:
            a, b = l.split("+", 1)
            if a in avail and b in avail:
                out.append(l)
        else:
            if l in avail:
                out.append(l)

    # fallback: minimal satu bahasa yang tersedia
    if not out and avail:
        out.append(sorted(avail)[0])
    return out or preferred


def _tesseract_cli(img: Image.Image, psm: int, lang: str) -> str:
    """
    Fallback paling stabil: panggil tesseract CLI.
    Ini meniru pendekatan v3: ada --tessdata-dir jika ketemu.
    """
    _configure_tesseract_once()

    exe = _resolve_tesseract_exe() or os.getenv("TESSERACT_EXE") or "tesseract"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    try:
        img.save(tmp.name)
        cmd = [exe, tmp.name, "stdout", "-l", lang, "--psm", str(psm), "--oem", "3", "--dpi", "300"]
        if _TESSDATA_DIR:
            cmd += ["--tessdata-dir", _TESSDATA_DIR]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        out = p.stdout.decode("utf-8", errors="ignore").strip()
        return out
    except Exception as e:
        print(f"[OCR][CLI] error: {e}")
        return ""
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def _ocr_with_tesseract(img: Image.Image) -> str:
    """
    OPTIMIZED STRATEGY:
    1. Coba metode tercepat dulu: PSM 6 (uniform block) dengan preprocessing
    2. Jika gagal, coba PSM 11 (sparse text) - bagus untuk teks dengan layout kompleks
    3. Skip PSM yang jarang berhasil (3,4,7,13) untuk speed
    4. Early exit saat sudah dapat hasil >= 5 chars
    """
    _configure_tesseract_once()

    try:
        import pytesseract
    except Exception:
        return ""

    langs = _pick_lang_try_order()
    # OPTIMIZED: Hanya PSM terbaik (6 = block text, 11 = sparse, 3 = auto sebagai fallback)
    psm_list = (6, 11, 3)

    # Kandidat: original + preprocessing variants (sudah dikurangi jadi 2)
    base = ImageOps.exif_transpose(img).convert("RGB")
    candidates: List[Image.Image] = [base]
    candidates += _cv2_preprocess_variants(base)  # Max 2 variants

    def run(im: Image.Image, psm: int, lang: str) -> str:
        try:
            result = (pytesseract.image_to_string(im, lang=lang, config=_tesseract_config(psm)) or "").strip()
            # Clean text immediately
            return _clean_ocr_text(result)
        except Exception:
            return ""

    best_result = ""
    
    # STRATEGY 1: Coba preprocessing variants dulu (sering lebih baik dari original)
    # Dengan PSM 6 (tercepat dan paling umum berhasil)
    for candidate in candidates[1:]:  # Skip original dulu
        for lang in langs:
            txt = run(candidate, psm=6, lang=lang)
            if len(txt) >= 5:
                return txt
            if len(txt) > len(best_result):
                best_result = txt
    
    # STRATEGY 2: Coba original + semua PSM
    for psm in psm_list:
        for lang in langs:
            txt = run(candidates[0], psm, lang)
            if len(txt) >= 5:
                return txt
            if len(txt) > len(best_result):
                best_result = txt
    
    # STRATEGY 3: Fallback CLI hanya jika pytesseract gagal total
    if not best_result:
        for candidate in candidates:
            for psm in (6, 11):  # Hanya 2 PSM tercepat
                for lang in langs:
                    txt = _tesseract_cli(candidate, psm=psm, lang=lang)
                    txt = _clean_ocr_text(txt)
                    if len(txt) >= 5:
                        return txt
                    if len(txt) > len(best_result):
                        best_result = txt

    return best_result


def ocr_image_bytes(image_bytes: bytes) -> str:
    """
    Extract dan bersihkan teks dari gambar.
    Text cleaning sudah dilakukan di _ocr_with_tesseract.
    """
    if not image_bytes:
        return ""

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        print(f"[OCR] cannot open image: {e}")
        return ""

    text = _ocr_with_tesseract(img)
    return (text or "").strip()


def ocr_video_bytes(video_bytes: bytes) -> Tuple[str, int]:
    """
    OPTIMIZED Video OCR:
    - Sample 10 frames (lebih banyak untuk hasil stabil)
    - Sampling merata untuk coverage maksimal
    - Text cleaning + deduplikasi
    """
    if not video_bytes:
        return "", 0

    try:
        import cv2
    except Exception:
        print("[OCR][VIDEO] opencv belum terpasang. Install: pip install opencv-python")
        return "", 0

    _configure_tesseract_once()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(video_bytes)
        tmp_path = f.name

    cap = cv2.VideoCapture(tmp_path)
    if not cap.isOpened():
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return "", 0

    # IMPROVED: Tingkatkan dari 5 ke 15 frames untuk hasil lebih stabil dan coverage maksimal
    # Video biasanya lebih challenging karena motion blur, lighting changes, dll
    max_frames = min(15, max(5, int(settings.video_max_frames)))

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    print(f"[OCR][VIDEO] Total frames: {total}, sampling {max_frames} frames")
    
    if total > 0:
        # Sample merata di seluruh video dengan spacing lebih baik
        # Hindari frame pertama/terakhir yang sering blur
        start_offset = max(1, total // 20)  # Skip 5% awal
        end_offset = max(1, total // 20)    # Skip 5% akhir
        safe_range = max(start_offset, total - end_offset - 1)
        
        if safe_range > max_frames:
            indices = np.linspace(start_offset, safe_range, num=max_frames, dtype=int).tolist()
        else:
            # Video pendek, ambil semua frames
            indices = list(range(0, total, max(1, total // max_frames)))
    else:
        # Fallback: stride
        stride = max(1, int(settings.video_frame_stride))
        indices = list(range(0, stride * max_frames, stride))
    
    print(f"[OCR][VIDEO] Frame indices to sample: {indices[:5]}... (total {len(indices)})")

    texts: List[str] = []
    used = 0

    for fi in indices:
        try:
            if total > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # BGR -> RGB -> PIL
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            
            # VIDEO-SPECIFIC: Apply stronger preprocessing untuk video frames
            # Video frames sering punya motion blur, compression artifacts
            # Resize jika terlalu besar (improve OCR accuracy)
            if img.size[0] > 1920 or img.size[1] > 1080:
                aspect = img.size[0] / img.size[1]
                if aspect > 1:
                    new_size = (1920, int(1920 / aspect))
                else:
                    new_size = (int(1080 * aspect), 1080)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Try multiple preprocessing attempts for better quality
            # Video frames need more aggressive approach
            t = _ocr_with_tesseract(img)  # Sudah include text cleaning
            
            # Validation: Minimal chars dan filtering noise
            cleaned_t = t.strip()
            if cleaned_t and len(cleaned_t) >= 5:  # Naikan dari 3 ke 5 untuk quality
                # Filter: pastikan ada minimal 3 kata readable (hindari noise)
                words = [w for w in cleaned_t.split() if len(w) >= 2]
                if len(words) >= 3:  # Minimal 3 kata
                    texts.append(cleaned_t)
                    print(f"[OCR][VIDEO] Frame {fi}: extracted {len(cleaned_t)} chars, {len(words)} words")
                else:
                    print(f"[OCR][VIDEO] Frame {fi}: skipped (only {len(words)} valid words)")
            used += 1
        except Exception as e:
            print(f"[OCR][VIDEO] Error on frame {fi}: {e}")
            continue

    cap.release()
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    # Deduplikasi: hapus teks duplikat dari frame yang mirip
    # Gunakan similarity check yang lebih ketat untuk video
    unique_texts = []
    seen = set()
    for t in texts:
        # Normalisasi untuk perbandingan (lowercase + strip whitespace)
        normalized = " ".join(t.lower().split())
        
        # Check similarity dengan texts yang sudah ada
        is_duplicate = False
        for existing_norm in seen:
            # Jika 80% mirip, anggap duplicate
            if len(normalized) > 0 and len(existing_norm) > 0:
                shorter = min(len(normalized), len(existing_norm))
                longer = max(len(normalized), len(existing_norm))
                # Simple similarity: check if one contains most of the other
                if normalized in existing_norm or existing_norm in normalized:
                    is_duplicate = True
                    break
                # Or if very similar length and prefix
                if abs(longer - shorter) < shorter * 0.2:  # Length difference < 20%
                    common_prefix = 0
                    for i in range(min(len(normalized), len(existing_norm))):
                        if normalized[i] == existing_norm[i]:
                            common_prefix += 1
                        else:
                            break
                    if common_prefix > shorter * 0.8:  # 80% same prefix
                        is_duplicate = True
                        break
        
        if not is_duplicate and normalized:
            seen.add(normalized)
            unique_texts.append(t)
    
    print(f"[OCR][VIDEO] Deduplication: {len(texts)} → {len(unique_texts)} unique texts")
    
    # Merge dan clean sekali lagi
    merged = "\n".join(unique_texts)
    merged = _clean_ocr_text(merged)
    
    print(f"[OCR][VIDEO] Final result: {len(merged)} chars from {used} frames, {len(unique_texts)} unique texts")
    print(f"[OCR][VIDEO] Preview: {merged[:150]}...")
    
    return merged, used