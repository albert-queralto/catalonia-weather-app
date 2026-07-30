from fastapi import APIRouter
from app.services.recommender import MLRecommender
from app.core.config import settings

model = MLRecommender(settings.model_path)
model.load()

router = APIRouter()


@router.get("/health")
def health() -> dict:
    model.load_if_stale()
    return {"ok": True, "status": "ok", "model_loaded": model.model is not None}
