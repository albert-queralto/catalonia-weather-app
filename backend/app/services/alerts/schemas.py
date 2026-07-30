from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class AvisAfectacio(BaseModel):
    dia: Optional[str] = None
    llindar: Optional[str] = None
    auxiliar: Optional[bool] = None
    perill: Optional[int] = None
    idComarca: Optional[int] = None
    nivell: Optional[int] = None

class Periode(BaseModel):
    nom: str
    afectacions: Optional[List[AvisAfectacio]] = None

class Evolucio(BaseModel):
    dia: str
    comentari: Optional[str] = None
    representatiu: Optional[int] = None
    llindar1: Optional[str] = None
    llindar2: Optional[str] = None
    distribucioGeografica: Optional[str] = None
    valorMaxim: Optional[str] = None
    periodes: List[Periode] = Field(default_factory=list)

class Avis(BaseModel):
    tipus: str
    dataEmisio: str
    dataInici: str
    dataFi: str
    estat: Optional[str] = None
    evolucions: List[Evolucio] = Field(default_factory=list)

class Meteor(BaseModel):
    nom: str

class Estat(BaseModel):
    nom: str
    data: Optional[str] = None

class EpisodiObert(BaseModel):
    estat: Estat
    meteor: Meteor
    avisos: List[Avis] = Field(default_factory=list)
    
    
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
