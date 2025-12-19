from pydantic import BaseModel
from typing import List, Optional, Any

class VariableLecture(BaseModel):
    data: str
    valor: float
    estat: str
    baseHoraria: str
    dataExtrem: Optional[str] = None

class Variable(BaseModel):
    codi: int
    lectures: List[VariableLecture]

class StationMeasuredData(BaseModel):
    codi: str
    variables: List[Variable]