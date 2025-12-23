from geoalchemy2.shape import to_shape
from app.db.models.activity_suggestion import ActivitySuggestion

def activity_to_schema(activity: ActivitySuggestion) -> dict:
    geom = to_shape(activity.location)
    return {
        "id": str(activity.id),
        "name": activity.name,
        "category": activity.category,
        "tags": activity.tags,
        "indoor": activity.indoor,
        "covered": activity.covered,
        "price_level": activity.price_level,
        "difficulty": activity.difficulty,
        "duration_minutes": activity.duration_minutes,
        "location": {
            "type": "Point",
            "coordinates": [geom.x, geom.y],
        },
        "created_at": activity.created_at.date() if activity.created_at else None,
        "validated": activity.validated,
    }