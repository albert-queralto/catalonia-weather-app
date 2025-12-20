from pydantic import BaseModel
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