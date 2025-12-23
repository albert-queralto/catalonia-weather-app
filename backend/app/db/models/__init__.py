# Import all models from their respective files
from .comarca import Comarca
from .meteocat import (
    MeteocatStation,
    StationMeasurement,
    StationVariable,
    StationVariableValue,
)
from .user import (
    User,
    UserPreference,
    Activity,
    Event
)


__all__ = [
    "Comarca",
    "MeteocatStation",
    "StationMeasurement",
    "StationVariable",
    "StationVariableValue",
    "User",
    "UserPreference",
    "Activity",
    "Event",
]