from fastapi import APIRouter, Query
from app.services.alerts.service import alerts_service
from app.services.alerts.schemas import EpisodiObert
from typing import List

router = APIRouter()

@router.get("/meteocat/episodis-oberts", response_model=List[EpisodiObert])
async def get_episodis_oberts(
    year: int = Query(..., ge=2000, le=2100, description="Year in YYYY format"),
    month: int = Query(..., ge=1, le=12, description="Month in MM format"),
    day: int = Query(..., ge=1, le=31, description="Day in DD format"),
):
    return await alerts_service.get_episodis_oberts(year, month, day)