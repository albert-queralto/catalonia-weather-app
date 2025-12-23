from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from app.db.session import get_session
from app.db.models.activity_suggestion import ActivitySuggestion
from app.services.activity.schemas import ActivitySuggestionIn, ActivitySuggestionOut
from app.services.activity.utils import activity_to_schema

router = APIRouter()

@router.get("/activities", response_model=list[ActivitySuggestionOut])
def list_activities(db: Session = Depends(get_session)):
    """List all activities (suggested and validated)."""
    activities = db.query(ActivitySuggestion).all()
    return [activity_to_schema(a) for a in activities]

@router.get("/activities/pending", response_model=list[ActivitySuggestionOut])
def list_pending_activities(db: Session = Depends(get_session)):
    """List all pending (not yet validated) activities."""
    pending_activities = db.query(ActivitySuggestion).filter_by(validated=False).all()
    return [activity_to_schema(a) for a in pending_activities]

@router.post("/activities/validate/{activity_id}", response_model=ActivitySuggestionOut)
def validate_activity(activity_id: str, db: Session = Depends(get_session)):
    """Validate a pending activity (admin only)."""
    activity = db.query(ActivitySuggestion).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    activity.validated = True
    db.commit()
    db.refresh(activity)
    return activity_to_schema(activity)

@router.post("/activities/suggest", response_model=ActivitySuggestionOut)
def suggest_activity(payload: ActivitySuggestionIn, db: Session = Depends(get_session)):
    """Suggest a new activity. The activity will be pending until validated by an admin."""
    geo_shape = shape(payload.location.dict())
    suggestion = ActivitySuggestion(
        id=str(uuid4()),
        name=payload.name,
        category=payload.category,
        tags=payload.tags,
        indoor=payload.indoor,
        covered=payload.covered,
        price_level=payload.price_level,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        location=from_shape(geo_shape, srid=4326),
        created_at=datetime.now(timezone.utc),
        validated=False
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return activity_to_schema(suggestion)

@router.delete("/activities/{activity_id}", response_model=dict)
def delete_activity(activity_id: str, db: Session = Depends(get_session)):
    """
    Delete an activity by its ID.

    Args:
        activity_id (str): The ID of the activity to delete.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: A message indicating the activity was deleted.

    Raises:
        HTTPException: If the activity is not found.
    """
    activity = db.query(ActivitySuggestion).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(activity)
    db.commit()
    return {"detail": "Activity deleted"}

@router.put("/activities/{activity_id}", response_model=ActivitySuggestionOut)
def update_activity(activity_id: str, payload: ActivitySuggestionIn, db: Session = Depends(get_session)):
    """
    Update an activity by its ID.

    Args:
        activity_id (str): The ID of the activity to update.
        payload (ActivitySuggestionIn): The new activity data.
        db (Session): SQLAlchemy database session.

    Returns:
        ActivitySuggestionOut: The updated activity.

    Raises:
        HTTPException: If the activity is not found.
    """
    activity = db.query(ActivitySuggestion).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    for field, value in payload.dict().items():
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return activity_to_schema(activity)