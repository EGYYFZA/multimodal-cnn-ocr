from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.web import router as web_router
from app.routes.predict import router as predict_router
from app.services.model_service import load_model_on_startup
from app.services.dataset_service import load_datasets_on_startup


def create_app() -> FastAPI:
    app = FastAPI(
        title="HoaxShield API",
        version="1.0.0",
        description="Deteksi berita hoaks menggunakan Multi-Kernel 1D CNN & OCR (gambar/video).",
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(web_router)
    app.include_router(predict_router, prefix="/api")

    app.add_event_handler("startup", load_model_on_startup)
    app.add_event_handler("startup", load_datasets_on_startup)

    return app

app = create_app()
