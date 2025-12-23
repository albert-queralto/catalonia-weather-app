from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from app.db.base import Base
from sqlalchemy import String


class Comarca(Base):
    __tablename__ = "comarcas"

    # Official comarca code (e.g., "BAR", "VLL" etc.). Primary key for stable joins.
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    # PostGIS geometry (WGS84).
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True))
