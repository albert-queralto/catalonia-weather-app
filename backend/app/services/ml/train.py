from __future__ import annotations

import importlib.util
import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sklearn.ensemble import (
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.core.config import settings
from app.db.models import MeteocatStation
from app.db.session import SessionLocal

FEATURE_COLUMNS = [
    "lag_1",
    "lag_2",
    "lag_3",
    "rolling_3",
    "rolling_24",
    "hour_sin",
    "hour_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "month",
    "is_weekend",
]

BASE_MODEL_NAMES = [
    "random_forest",
    "gradient_boosting",
    "hist_gradient_boosting",
    "ridge",
]

VARIABLE_ALIASES = {
    "precipitation": {
        "precipitation",
        "precipitacio",
        "precipitacion",
        "pluja",
        "rain",
        "ppt",
    },
    "precipitacio": {
        "precipitation",
        "precipitacio",
        "precipitacion",
        "pluja",
        "rain",
        "ppt",
    },
    "temperature": {"temperature", "temperatura", "temp", "ta"},
    "temperatura": {"temperature", "temperatura", "temp", "ta"},
    "wind": {"wind", "vent", "velocitat vent", "vv"},
    "vent": {"wind", "vent", "velocitat vent", "vv"},
}


def available_model_names() -> list[str]:
    names = list(BASE_MODEL_NAMES)

    if importlib.util.find_spec("xgboost") is not None:
        names.append("xgboost")
    if importlib.util.find_spec("lightgbm") is not None:
        names.append("lightgbm")

    return names


def fetch_all_stations(db: Session | None = None) -> list[dict[str, Any]]:
    def fetch(session: Session) -> list[dict[str, Any]]:
        rows = session.execute(
            select(MeteocatStation.codi, MeteocatStation.nom).order_by(MeteocatStation.codi)
        ).all()
        return [{"codi": row.codi, "nom": row.nom} for row in rows]

    if db is not None:
        return fetch(db)

    with SessionLocal() as session:
        return fetch(session)


def train_and_save_model(
    station_code: str,
    date_from: str | date | datetime,
    date_to: str | date | datetime,
    target_variable: str | int,
    model_name: str,
    db: Session,
) -> dict[str, Any]:
    start_date = _as_date(date_from)
    end_date = _as_date(date_to)

    if end_date < start_date:
        raise ValueError("date_to must be greater than or equal to date_from")

    station = db.execute(
        select(MeteocatStation).where(MeteocatStation.codi == station_code)
    ).scalar_one_or_none()
    if not station:
        raise ValueError(f"Station not found: {station_code}")

    variable = _resolve_station_variable(db, station_code, target_variable)
    values = _load_station_values(
        db,
        station_code=station_code,
        variable_code=int(variable["codi"]),
        date_from=start_date,
        date_to=end_date,
    )

    if len(values) < 12:
        raise ValueError(
            f"Not enough measurements to train {station_code}: found {len(values)}, need at least 12"
        )

    train_frame = _build_training_frame(values)
    if len(train_frame) < 8:
        raise ValueError(
            f"Not enough lagged measurements to train {station_code}: found {len(train_frame)}, need at least 8"
        )

    model = _make_model(model_name)
    X = train_frame[FEATURE_COLUMNS].astype(float)
    y = train_frame["target"].astype(float)

    split_at = max(1, int(len(train_frame) * 0.8))
    if len(train_frame) >= 20 and split_at < len(train_frame):
        X_train = X.iloc[:split_at]
        y_train = y.iloc[:split_at]
        X_eval = X.iloc[split_at:]
        y_eval = y.iloc[split_at:]
        evaluation = "holdout"
    else:
        X_train = X
        y_train = y
        X_eval = X
        y_eval = y
        evaluation = "in_sample"

    model.fit(X_train, y_train)
    predictions = model.predict(X_eval)
    metrics = _regression_metrics(y_eval, predictions)

    trained_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "model": model,
        "model_name": _normalise_model_name(model_name),
        "feature_order": FEATURE_COLUMNS,
        "station_code": station_code,
        "station_name": station.nom,
        "variable_code": int(variable["codi"]),
        "variable_name": variable["nom"],
        "target_variable": str(target_variable),
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
        "training_rows": int(len(X_train)),
        "evaluation_rows": int(len(X_eval)),
        "evaluation": evaluation,
        "metrics": metrics,
        "trained_at": trained_at,
    }

    model_path = _station_model_path(
        station_code=station_code,
        variable_code=int(variable["codi"]),
        model_name=_normalise_model_name(model_name),
    )
    model_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = model_path.with_suffix(f"{model_path.suffix}.tmp")
    joblib.dump(payload, tmp_path)
    tmp_path.replace(model_path)

    return {
        "status": "ok",
        "model_path": str(model_path),
        "station_code": station_code,
        "station_name": station.nom,
        "variable_code": int(variable["codi"]),
        "variable_name": variable["nom"],
        "model_name": payload["model_name"],
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
        "rows": int(len(train_frame)),
        "training_rows": payload["training_rows"],
        "evaluation_rows": payload["evaluation_rows"],
        "evaluation": evaluation,
        "metrics": metrics,
        "trained_at": trained_at,
    }


def _as_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _normalise(value: Any) -> str:
    text_value = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = text_value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.lower()).strip()


def _normalise_model_name(value: str) -> str:
    return _normalise(value).replace("-", "_").replace(" ", "_")


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", _normalise(value).replace(" ", "_")).strip("_")


def _aliases_for(value: str) -> set[str]:
    normalised = _normalise(value)
    return VARIABLE_ALIASES.get(normalised, {normalised})


def _resolve_station_variable(
    db: Session,
    station_code: str,
    target_variable: str | int,
) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT
                sv.codi AS codi,
                sv.nom AS nom,
                sv.acronim AS acronim
            FROM station_measurements m
            JOIN station_variable_values v
                ON v.measurement_id = m.id
            JOIN station_variables sv
                ON sv.codi = v.codi_variable
            WHERE m.codi_estacio = :station_code
            ORDER BY sv.codi
            """
        ),
        {"station_code": station_code},
    ).mappings().all()

    if not rows:
        raise ValueError(f"No measured variables found for station {station_code}")

    wanted = _normalise(target_variable)
    if wanted.isdigit():
        for row in rows:
            if str(row["codi"]) == wanted:
                return dict(row)

    aliases = _aliases_for(wanted)

    for row in rows:
        candidate_values = [
            _normalise(row["nom"]),
            _normalise(row["acronim"]),
            str(row["codi"]),
        ]
        if wanted in candidate_values:
            return dict(row)

    for row in rows:
        candidate_text = " ".join(
            [
                _normalise(row["nom"]),
                _normalise(row["acronim"]),
                str(row["codi"]),
            ]
        )
        if any(alias and alias in candidate_text for alias in aliases):
            return dict(row)

    available = ", ".join(
        f"{row['codi']}:{row['nom'] or row['acronim'] or 'unnamed'}" for row in rows[:15]
    )
    raise ValueError(
        f"Variable '{target_variable}' was not found for station {station_code}. "
        f"Available variables include: {available}"
    )


def _load_station_values(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    date_from: date,
    date_to: date,
) -> pd.DataFrame:
    rows = db.execute(
        text(
            """
            SELECT
                COALESCE(v.data, m.date) AS measured_at,
                AVG(v.valor) AS value
            FROM station_measurements m
            JOIN station_variable_values v
                ON v.measurement_id = m.id
            WHERE m.codi_estacio = :station_code
              AND v.codi_variable = :variable_code
              AND COALESCE(v.data, m.date) >= :start_dt
              AND COALESCE(v.data, m.date) < :end_dt
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {
            "station_code": station_code,
            "variable_code": variable_code,
            "start_dt": datetime.combine(date_from, time.min),
            "end_dt": datetime.combine(date_to + timedelta(days=1), time.min),
        },
    ).mappings().all()

    frame = pd.DataFrame([dict(row) for row in rows], columns=["measured_at", "value"])
    if frame.empty:
        return frame

    frame["measured_at"] = pd.to_datetime(frame["measured_at"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["measured_at", "value"]).sort_values("measured_at")
    return frame.reset_index(drop=True)


def _build_training_frame(values: pd.DataFrame) -> pd.DataFrame:
    frame = values.copy()
    measured_at = pd.to_datetime(frame["measured_at"])

    frame["lag_1"] = frame["value"].shift(1)
    frame["lag_2"] = frame["value"].shift(2)
    frame["lag_3"] = frame["value"].shift(3)
    frame["rolling_3"] = frame["value"].shift(1).rolling(window=3, min_periods=1).mean()
    frame["rolling_24"] = frame["value"].shift(1).rolling(window=24, min_periods=1).mean()

    hour_angle = 2 * np.pi * measured_at.dt.hour / 24
    day_angle = 2 * np.pi * measured_at.dt.dayofyear / 366
    frame["hour_sin"] = np.sin(hour_angle)
    frame["hour_cos"] = np.cos(hour_angle)
    frame["day_of_year_sin"] = np.sin(day_angle)
    frame["day_of_year_cos"] = np.cos(day_angle)
    frame["month"] = measured_at.dt.month
    frame["is_weekend"] = measured_at.dt.dayofweek.isin([5, 6]).astype(float)
    frame["target"] = frame["value"]

    return frame.dropna(subset=FEATURE_COLUMNS + ["target"]).reset_index(drop=True)


def _make_model(model_name: str):
    name = _normalise_model_name(model_name)

    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=250,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

    if name == "gradient_boosting":
        return GradientBoostingRegressor(random_state=42)

    if name == "hist_gradient_boosting":
        return HistGradientBoostingRegressor(random_state=42)

    if name == "ridge":
        return Ridge(alpha=1.0)

    if name == "xgboost":
        from xgboost import XGBRegressor

        return XGBRegressor(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=1,
        )

    if name == "lightgbm":
        import lightgbm as lgb

        return lgb.LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            verbose=-1,
        )

    raise ValueError(
        f"Unsupported model '{model_name}'. Supported models: {', '.join(available_model_names())}"
    )


def _regression_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float | None]:
    y_true_arr = np.asarray(list(y_true), dtype=float)
    y_pred_arr = np.asarray(list(y_pred), dtype=float)

    if len(y_true_arr) == 0:
        return {"mae": None, "rmse": None, "r2": None}

    r2 = None
    if len(y_true_arr) > 1 and len(np.unique(y_true_arr)) > 1:
        r2 = float(r2_score(y_true_arr, y_pred_arr))

    return {
        "mae": float(mean_absolute_error(y_true_arr, y_pred_arr)),
        "rmse": float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr))),
        "r2": r2,
    }


def _station_model_path(*, station_code: str, variable_code: int, model_name: str) -> Path:
    output_dir = Path(settings.station_model_dir)
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir

    filename = f"{_slug(station_code)}_{variable_code}_{_slug(model_name)}.joblib"
    return output_dir / filename
