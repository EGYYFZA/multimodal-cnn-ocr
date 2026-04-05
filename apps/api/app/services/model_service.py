import os
import pickle
from typing import Dict, Any, Optional, Tuple

import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences

from app.services.config import settings
from app.services.preprocess import clean_text

_MODEL: Optional[tf.keras.Model] = None
_TOK = None
_MAX_LEN: Optional[int] = None

_MODEL_PATH_ACTIVE: Optional[str] = None
_TOK_PATH_ACTIVE: Optional[str] = None
_OUTPUT_MODE: str = "unknown"  # "softmax2" | "sigmoid1" | "unknown"


def _pick_existing_path(candidates: Tuple[str, ...]) -> Optional[str]:
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


def load_model_on_startup() -> None:
    global _MODEL, _TOK, _MAX_LEN, _MODEL_PATH_ACTIVE, _TOK_PATH_ACTIVE, _OUTPUT_MODE

    model_path = settings.model_path
    tok_path = settings.tokenizer_path

    if not model_path or not os.path.exists(model_path):
        model_path = _pick_existing_path((
            "app/assets/multi_kernel_model.h5",
            "app/assets/mkcnn_best.keras",
            "app/assets/mkcnn_model.keras",
            "multi_kernel_model.h5",
            "mkcnn_best.keras",
            "mkcnn_model.keras",
        ))
    if not model_path:
        raise FileNotFoundError("Model tidak ditemukan. Taruh di app/assets/ atau set MODEL_PATH.")

    if not tok_path or not os.path.exists(tok_path):
        tok_path = _pick_existing_path((
            "app/assets/tokenizer.pkl",
            "tokenizer.pkl",
        ))
    if not tok_path:
        raise FileNotFoundError("Tokenizer tidak ditemukan. Taruh di app/assets/ atau set TOKENIZER_PATH.")

    _MODEL = tf.keras.models.load_model(model_path, compile=False)

    with open(tok_path, "rb") as f:
        tok_bundle = pickle.load(f)

    tok_max_len = 0
    if isinstance(tok_bundle, dict) and "tokenizer" in tok_bundle:
        _TOK = tok_bundle["tokenizer"]
        tok_max_len = int(tok_bundle.get("max_len", 0) or 0)
    else:
        _TOK = tok_bundle

    # MAX_LEN: prefer model input length, fallback tokenizer bundle, fallback env, fallback 150 (default training)
    maxlen = None
    try:
        ish = getattr(_MODEL, "input_shape", None)
        if ish and isinstance(ish, tuple) and len(ish) >= 2 and isinstance(ish[1], int):
            maxlen = int(ish[1])
    except Exception:
        maxlen = None

    if not maxlen:
        maxlen = tok_max_len if tok_max_len > 0 else int(os.getenv("MAX_LEN", "150"))
    _MAX_LEN = int(maxlen)

    # Detect output mode
    _OUTPUT_MODE = "unknown"
    try:
        osh = getattr(_MODEL, "output_shape", None)
        if isinstance(osh, tuple) and len(osh) >= 2 and isinstance(osh[-1], int):
            out_dim = int(osh[-1])
            if out_dim == 2:
                _OUTPUT_MODE = "softmax2"
            elif out_dim == 1:
                _OUTPUT_MODE = "sigmoid1"
    except Exception:
        _OUTPUT_MODE = "unknown"

    _MODEL_PATH_ACTIVE = model_path
    _TOK_PATH_ACTIVE = tok_path


def _ensure_loaded():
    if _MODEL is None or _TOK is None or _MAX_LEN is None:
        load_model_on_startup()


def _prob_hoax_from_pred(y: np.ndarray) -> float:
    arr = np.asarray(y)
    # softmax 2-class: [p_valid, p_hoax]
    if arr.ndim == 2 and arr.shape[1] == 2:
        return float(arr[0, 1])
    # sigmoid 1-class: [p_hoax]
    if arr.ndim == 2 and arr.shape[1] == 1:
        return float(arr[0, 0])
    flat = arr.ravel()
    return float(flat[0]) if flat.size else 0.0


def predict_proba(text: str, *, padding: str = "post", truncating: str = "post") -> float:
    _ensure_loaded()

    s = clean_text(text)
    if not s:
        return 0.0

    seq = _TOK.texts_to_sequences([s])
    if not seq or not seq[0]:
        return 0.0

    x = pad_sequences(seq, maxlen=_MAX_LEN, padding=padding, truncating=truncating)
    y = _MODEL.predict(x, verbose=0)
    p = _prob_hoax_from_pred(y)
    return max(0.0, min(1.0, float(p)))


def decide_label(prob_hoax: float, tau: float) -> str:
    """
    Konsisten dengan simulasi final:
    - softmax2: threshold tetap 0.5
    - sigmoid1: threshold = tau
    """
    _ensure_loaded()
    thr = 0.5 if _OUTPUT_MODE == "softmax2" else float(tau)
    return "HOAKS" if float(prob_hoax) >= thr else "VALID"


def get_confidence_level(prob_hoax: float, tau: Optional[float] = None) -> Dict[str, Any]:
    _ensure_loaded()
    thr = 0.5 if _OUTPUT_MODE == "softmax2" else float(tau if tau is not None else settings.operating_tau)
    p = float(prob_hoax)
    margin = abs(p - thr)

    if margin >= 0.25:
        level = "TINGGI"
    elif margin >= 0.15:
        level = "SEDANG"
    else:
        level = "RENDAH"

    return {"level": level, "threshold": thr, "margin": margin}


def model_info() -> Dict[str, Any]:
    _ensure_loaded()
    return {
        "max_len": _MAX_LEN,
        "output_mode": _OUTPUT_MODE,
        "threshold_default": 0.5 if _OUTPUT_MODE == "softmax2" else float(settings.operating_tau),
        "model_path_active": _MODEL_PATH_ACTIVE,
        "tokenizer_path_active": _TOK_PATH_ACTIVE,
        "model_input_shape": getattr(_MODEL, "input_shape", None),
        "model_output_shape": getattr(_MODEL, "output_shape", None),
        "tf_version": tf.__version__,
    }