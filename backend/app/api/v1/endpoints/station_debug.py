from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session

router = APIRouter()


@router.get("/debug/station-data-summary")
def station_data_summary(db: Session = Depends(get_session)):
    counts = db.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*) FROM meteocat_stations) AS stations,
              (SELECT COUNT(*) FROM station_variables) AS variables,
              (SELECT COUNT(*) FROM station_measurements) AS measurements,
              (SELECT COUNT(*) FROM station_variable_values) AS values
            """
        )
    ).mappings().first()

    latest = db.execute(
        text(
            """
            SELECT
              m.codi_estacio,
              s.nom AS station_name,
              m.date,
              v.codi_variable,
              sv.nom AS variable_name,
              sv.unitat,
              COUNT(*) AS value_count,
              MIN(v.data) AS first_value_time,
              MAX(v.data) AS last_value_time
            FROM station_measurements m
            JOIN station_variable_values v
              ON v.measurement_id = m.id
            LEFT JOIN meteocat_stations s
              ON s.codi = m.codi_estacio
            LEFT JOIN station_variables sv
              ON sv.codi = v.codi_variable
            GROUP BY
              m.codi_estacio,
              s.nom,
              m.date,
              v.codi_variable,
              sv.nom,
              sv.unitat
            ORDER BY m.date DESC, value_count DESC
            LIMIT 50
            """
        )
    ).mappings().all()

    return {
        "counts": dict(counts or {}),
        "latest_station_variable_days": [dict(row) for row in latest],
    }