from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any

class AvisAfectacio(BaseModel):
    dia: str
    llindar: Optional[str]
    auxiliar: Optional[bool]
    perill: Optional[int]
    idComarca: Optional[int]
    nivell: Optional[int]

class Periode(BaseModel):
    nom: str
    afectacions: Optional[List[AvisAfectacio]]

class Evolucio(BaseModel):
    dia: str
    comentari: Optional[str]
    representatiu: Optional[int]
    llindar1: Optional[str]
    llindar2: Optional[str]
    distribucioGeografica: Optional[str]
    periodes: List[Periode]

class Avis(BaseModel):
    tipus: str
    dataEmisio: str
    dataInici: str
    dataFi: str
    evolucions: List[Evolucio]

class Meteor(BaseModel):
    nom: str

class Estat(BaseModel):
    nom: str
    data: Optional[str]

class EpisodiObert(BaseModel):
    estat: Estat
    meteor: Meteor
    avisos: List[Avis]
    
    
class AlertComarcaOut(BaseModel):
    code: str
    name: str
    severity: int
    threshold: Optional[str] = None


class AffectedActivityOut(BaseModel):
    id: str
    name: str
    category: str
    indoor: bool


class AlertActionCard(BaseModel):
    id: str

    meteor: str
    severity: int
    severity_label: str

    starts_at: datetime
    ends_at: datetime

    affected_comarques: List[AlertComarcaOut] = Field(default_factory=list)

    recommended_action: str
    recommender_effect: str

    affected_recommended_activities: List[AffectedActivityOut] = Field(default_factory=list)


class AlertTimelineSlot(BaseModel):
    label: str
    starts_at: datetime
    ends_at: datetime
    max_severity: int = 0
    cards: List[AlertActionCard] = Field(default_factory=list)