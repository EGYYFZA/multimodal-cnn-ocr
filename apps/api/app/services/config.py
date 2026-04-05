import os
from dataclasses import dataclass
 
@dataclass(frozen=True)
class Settings:
    # Default pakai model multi-kernel dari notebook
    model_path: str = os.getenv("MODEL_PATH", "app/assets/multi_kernel_model.h5")
    tokenizer_path: str = os.getenv("TOKENIZER_PATH", "app/assets/tokenizer.pkl")

    operating_tau: float = float(os.getenv("OPERATING_TAU", "0.45"))

    # Opsional: match notebook dengan NLTK stopwords (kalau corpus tersedia)
    use_nltk_stopwords: bool = os.getenv("USE_NLTK_STOPWORDS", "0").strip().lower() not in ("0","false","no")

    max_text_chars: int = int(os.getenv("MAX_TEXT_CHARS", "12000"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))

    tesseract_exe: str = os.getenv("TESSERACT_EXE", "")
    tesseract_data_prefix: str = os.getenv("TESSDATA_PREFIX", "")

    video_max_frames: int = int(os.getenv("VIDEO_MAX_FRAMES", "10"))
    video_frame_stride: int = int(os.getenv("VIDEO_FRAME_STRIDE", "10"))

settings = Settings()
