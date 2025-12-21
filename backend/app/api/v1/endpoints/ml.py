from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.services.ml import train

router = APIRouter()

class TrainRequest(BaseModel):
    station_code: str
    date_from: str
    date_to: str
    target_variable: str = "Precipitation"
    model_name: str = "random_forest"

@router.get("/ml/models")
def list_models():
    return {"models": train.get_available_models()}

@router.post("/ml/train")
def train_model(
    req: TrainRequest,
    session: Session = Depends(get_session)
):
    try:
        model_path = train.train_and_save_model(
            req.station_code, 
            req.date_from, 
            req.date_to, 
            req.target_variable, 
            req.model_name, 
            session
        )
        return {"model_path": model_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))