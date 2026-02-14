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

router = APIRouter(prefix="/activities", tags=["activities"])

@router.get("/", response_model=list[ActivitySuggestionOut])
def list_activities(db: Session = Depends(get_session)):
    """List all activities (suggested and validated)."""
    activities = db.query(ActivitySuggestion).all()
    return [activity_to_schema(a) for a in activities]

@router.get("/pending", response_model=list[ActivitySuggestionOut])
def list_pending_activities(db: Session = Depends(get_session)):
    """List all pending (not yet validated) activities."""
    pending_activities = db.query(ActivitySuggestion).filter_by(validated=False).all()
    return [activity_to_schema(a) for a in pending_activities]

@router.post("/validate/{activity_id}", response_model=ActivitySuggestionOut)
def validate_activity(activity_id: str, db: Session = Depends(get_session)):
    """Validate a pending activity (admin only)."""
    activity = db.query(ActivitySuggestion).filter_by(id=activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    activity.validated = True
    db.commit()
    db.refresh(activity)
    return activity_to_schema(activity)

@router.post("/suggest", response_model=ActivitySuggestionOut)
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

@router.delete("/{activity_id}", response_model=dict)
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

@router.put("/{activity_id}", response_model=ActivitySuggestionOut)
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
        if field == "location":
            geo_shape = shape(value)
            value = from_shape(geo_shape, srid=4326)
        if field == "created_at":
            continue
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return activity_to_schema(activity)

@router.get("/categories", response_model=list[str])
def list_activity_categories(db: Session = Depends(get_session)):
    """
    Get all distinct activity categories.
    """
    categories = db.query(ActivitySuggestion.category).distinct().all()
    return [c[0] for c in categories if c[0] is not None]

# Add these imports at the top if not already present
import random
from datetime import timedelta
from typing import Optional
from pydantic import BaseModel

# Add this schema class after the imports
class PopulateActivitiesRequest(BaseModel):
    count: int = 100
    clear_existing: bool = False

# Add this endpoint at the end of the file
@router.post("/populate")
def populate_activities(
    request: PopulateActivitiesRequest, 
    db: Session = Depends(get_session)
):
    """
    Populate the database with synthetic activities for testing.
    """
    from sqlalchemy import text
    
    # Categories
    CATEGORIES = ["Sport", "Culture", "Nature", "Food", "Leisure", "Other"]
    
    # Activity templates by category
    ACTIVITY_NAMES = {
        "Sport": ["Beach Volleyball", "Mountain Biking", "Rock Climbing", "Kayaking", "Tennis", "Hiking", "Swimming", "Skateboarding", "Yoga", "Running"],
        "Culture": ["Art Gallery", "Museum", "Theater", "Concert Hall", "Cultural Center", "Cinema", "Jazz Club", "Exhibition"],
        "Nature": ["Botanical Garden", "Nature Reserve", "Forest Trail", "Waterfall", "Beach", "Mountain Summit", "Lake", "Natural Park"],
        "Food": ["Local Market", "Wine Tasting", "Cooking Class", "Food Tour", "Restaurant", "Tapas Bar", "Brewery"],
        "Leisure": ["Shopping District", "Park", "Escape Room", "Spa", "Boat Ride", "Mini Golf", "Aquarium"],
        "Other": ["Viewpoint", "Tourist Center", "Marketplace", "Photo Spot", "Public Square", "Observatory"]
    }
    
    TAGS_BY_CATEGORY = {
        "Sport": ["outdoor", "fitness", "team", "water", "family"],
        "Culture": ["indoor", "art", "music", "educational", "evening"],
        "Nature": ["outdoor", "scenic", "hiking", "peaceful", "photography"],
        "Food": ["local", "traditional", "gourmet", "budget-friendly"],
        "Leisure": ["fun", "relaxing", "family", "romantic"],
        "Other": ["sightseeing", "historic", "free", "popular"]
    }
    
    # Barcelona area bounds
    BARCELONA_LAT = 41.3851
    BARCELONA_LON = 2.1734
    RADIUS_KM = 25
    
    try:
        # Clear existing if requested
        if request.clear_existing:
            db.execute(text("DELETE FROM events"))
            db.execute(text("DELETE FROM activities"))
            db.commit()
        
        activities_created = []
        
        for i in range(request.count):
            # Random category
            category = random.choice(CATEGORIES)
            
            # Random name from category
            base_name = random.choice(ACTIVITY_NAMES.get(category, ["Activity"]))
            descriptors = ["North", "South", "East", "West", "Central", "Urban"]
            name = f"{random.choice(descriptors)} {base_name}" if random.random() < 0.4 else base_name
            
            # Random tags
            available_tags = TAGS_BY_CATEGORY.get(category, ["general"])
            num_tags = random.randint(2, min(4, len(available_tags)))
            tags = random.sample(available_tags, num_tags)
            
            # Indoor probability varies by category
            indoor_prob = {"Sport": 0.3, "Culture": 0.7, "Nature": 0.05, "Food": 0.6, "Leisure": 0.5, "Other": 0.4}.get(category, 0.3)
            indoor = random.random() < indoor_prob
            covered = indoor or (random.random() < 0.2)
            
            # Random attributes
            price_level = random.choices([0, 1, 2, 3, 4], weights=[20, 35, 25, 15, 5])[0]
            difficulty = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
            duration_minutes = random.choice([30, 60, 90, 120, 180, 240, 360])
            
            # Random location near Barcelona
            radius_km = random.uniform(0, RADIUS_KM)
            lat_offset = (radius_km / 111.0) * random.choice([-1, 1])
            lon_offset = (radius_km / (111.0 * 0.75)) * random.choice([-1, 1])
            lat = round(BARCELONA_LAT + lat_offset, 6)
            lon = round(BARCELONA_LON + lon_offset, 6)
            
            # Create activity
            activity = ActivitySuggestion(
                id=str(uuid4()),
                name=name,
                category=category,
                tags=tags,
                indoor=indoor,
                covered=covered,
                price_level=price_level,
                difficulty=difficulty,
                duration_minutes=duration_minutes,
                location=f"SRID=4326;POINT({lon} {lat})",
                validated=random.random() < 0.8,  # 80% validated
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))
            )
            
            db.add(activity)
            activities_created.append({
                "id": activity.id,
                "name": activity.name,
                "category": activity.category
            })
        
        db.commit()
        
        # Summary by category
        category_counts = {}
        for act in activities_created:
            cat = act["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "message": f"Successfully created {len(activities_created)} activities",
            "count": len(activities_created),
            "breakdown": category_counts,
            "samples": activities_created[:5]  # First 5 as examples
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to populate activities: {str(e)}")