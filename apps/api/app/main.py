from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.web import router as web_router
from app.routes.predict import router as predict_router
from app.services.model_service import load_model_on_startup
from app.services.dataset_service import load_datasets_on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model_on_startup()
    load_datasets_on_startup()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="HoaxShield API",
        version="1.0.0",
        description="Deteksi berita hoaks menggunakan Multi-Kernel 1D CNN & OCR (gambar/video).",
        lifespan=lifespan,
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(web_router)
    app.include_router(predict_router, prefix="/api")

    return app

app = create_app()
