from __future__ import annotations

import importlib.util
import json
import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

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

MODEL_REGISTRY_FILENAME = "registry.json"

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


def train_station_models_batch(
    db: Session,
    *,
    target_variable: str | int = "Precipitation",
    model_name: str = "xgboost",
    station_codes: Sequence[str] | None = None,
    station_limit: int | None = None,
    date_from: str | date | datetime | None = None,
    date_to: str | date | datetime | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Train station models in a batch, using each station's data range by default."""
    if station_limit is not None and station_limit <= 0:
        raise ValueError("station_limit must be greater than 0")

    normalised_model_name = _normalise_model_name(model_name)
    if normalised_model_name not in available_model_names():
        raise ValueError(
            f"Unsupported model '{model_name}'. Supported models: {', '.join(available_model_names())}"
        )

    start_override = _as_date(date_from) if date_from is not None else None
    end_override = _as_date(date_to) if date_to is not None else None
    if start_override and end_override and end_override < start_override:
        raise ValueError("date_to must be greater than or equal to date_from")

    started_at = datetime.now(timezone.utc)
    stations = _fetch_training_stations(
        db,
        station_codes=station_codes,
        station_limit=station_limit,
    )
    total = len(stations)
    trained = 0
    skipped = 0
    trained_models: list[dict[str, Any]] = []
    skipped_stations: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    for index, station in enumerate(stations, start=1):
        station_code = str(station["codi"])

        def publish_progress() -> None:
            if progress_callback is None:
                return
            progress_callback(
                {
                    "current": index,
                    "total": total,
                    "station_code": station_code,
                    "trained": trained,
                    "skipped": skipped,
                    "failed": len(failures),
                }
            )

        try:
            range_start, range_end = station_variable_date_range(
                db,
                station_code=station_code,
                target_variable=target_variable,
            )
            train_from = start_override or range_start
            train_to = end_override or range_end

            if train_from is None or train_to is None:
                skipped += 1
                skipped_stations.append(
                    {
                        "station_code": station_code,
                        "reason": "No measurements found for target variable",
                    }
                )
                publish_progress()
                continue

            result = train_and_save_model(
                station_code,
                train_from,
                train_to,
                target_variable,
                normalised_model_name,
                db,
            )
            trained += 1
            trained_models.append(result)
        except ValueError as exc:
            skipped += 1
            skipped_stations.append({"station_code": station_code, "reason": str(exc)})
        except Exception as exc:
            failures.append({"station_code": station_code, "error": str(exc)})

        publish_progress()

    finished_at = datetime.now(timezone.utc)
    status = "ok"
    if total == 0:
        status = "no_stations"
    elif failures and trained == 0:
        status = "failed"
    elif failures or skipped:
        status = "partial"

    return {
        "status": status,
        "target_variable": str(target_variable),
        "model_name": normalised_model_name,
        "date_from": start_override.isoformat() if start_override else None,
        "date_to": end_override.isoformat() if end_override else None,
        "stations": total,
        "trained": trained,
        "skipped": skipped,
        "failed": len(failures),
        "trained_models": trained_models,
        "skipped_stations": skipped_stations[:50],
        "failures": failures[:25],
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
    }


def station_variable_date_range(
    db: Session,
    *,
    station_code: str,
    target_variable: str | int,
) -> tuple[date | None, date | None]:
    variable = _resolve_station_variable(db, station_code, target_variable)
    row = db.execute(
        text(
            """
            SELECT
                MIN(COALESCE(v.data, m.date)) AS first_seen,
                MAX(COALESCE(v.data, m.date)) AS last_seen
            FROM station_measurements m
            JOIN station_variable_values v
                ON v.measurement_id = m.id
            WHERE m.codi_estacio = :station_code
              AND v.codi_variable = :variable_code
            """
        ),
        {
            "station_code": station_code,
            "variable_code": int(variable["codi"]),
        },
    ).mappings().one()

    return _maybe_date(row["first_seen"]), _maybe_date(row["last_seen"])


def list_trained_models() -> list[dict[str, Any]]:
    output_dir = station_model_dir()
    if not output_dir.exists():
        return []

    registry = read_model_registry()
    models = [
        _model_summary(path, registry)
        for path in output_dir.glob("*.joblib")
        if path.is_file()
    ]

    return sorted(
        models,
        key=lambda model: str(model.get("trained_at") or model.get("modified_at") or ""),
        reverse=True,
    )


def get_trained_model(model_id: str) -> dict[str, Any]:
    path = _safe_model_path(model_id)
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {model_id}")

    return _model_summary(path, read_model_registry(), include_features=True)


def activate_trained_model(model_id: str) -> dict[str, Any]:
    path = _safe_model_path(model_id)
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {model_id}")

    registry = read_model_registry()
    summary = _model_summary(path, registry, include_features=True)

    if summary.get("load_error"):
        raise ValueError(f"Cannot activate unreadable model: {summary['load_error']}")
    if not summary.get("station_code") or summary.get("variable_code") is None:
        raise ValueError("Cannot activate a model without station and variable metadata")

    key = _active_key(str(summary["station_code"]), int(summary["variable_code"]))
    registry.setdefault("active", {})[key] = model_id
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_model_registry(registry)

    summary["active"] = True
    return summary


def delete_trained_model(model_id: str) -> dict[str, Any]:
    path = _safe_model_path(model_id)
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {model_id}")

    registry = read_model_registry()
    removed_active_keys = [
        key
        for key, active_model_id in registry.get("active", {}).items()
        if active_model_id == model_id
    ]

    for key in removed_active_keys:
        registry["active"].pop(key, None)

    path.unlink()

    if removed_active_keys:
        registry["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_model_registry(registry)

    return {
        "status": "deleted",
        "model_id": model_id,
        "removed_active_keys": removed_active_keys,
    }


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

    trained_at_dt = datetime.now(timezone.utc)
    trained_at = trained_at_dt.isoformat()
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
        "rows": int(len(train_frame)),
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
        trained_at=trained_at_dt,
    )
    model_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = model_path.with_suffix(f"{model_path.suffix}.tmp")
    joblib.dump(payload, tmp_path)
    tmp_path.replace(model_path)

    model_id = model_path.name
    activate_trained_model(model_id)

    return {
        "status": "ok",
        "model_id": model_id,
        "model_path": str(model_path),
        "active": True,
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


def _maybe_date(value: Any) -> date | None:
    if value is None:
        return None
    return _as_date(value)


def _fetch_training_stations(
    db: Session,
    *,
    station_codes: Sequence[str] | None,
    station_limit: int | None,
) -> list[dict[str, Any]]:
    cleaned_codes = [
        str(code).strip()
        for code in station_codes or []
        if str(code).strip()
    ]
    if station_codes is not None and not cleaned_codes:
        return []

    stmt = select(MeteocatStation.codi, MeteocatStation.nom).order_by(MeteocatStation.codi)
    if cleaned_codes:
        stmt = stmt.where(MeteocatStation.codi.in_(cleaned_codes))
    if station_limit is not None:
        stmt = stmt.limit(station_limit)

    rows = db.execute(stmt).all()
    return [{"codi": row.codi, "nom": row.nom} for row in rows]


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


def station_model_dir() -> Path:
    output_dir = Path(settings.station_model_dir)
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    return output_dir


def read_model_registry() -> dict[str, Any]:
    path = station_model_dir() / MODEL_REGISTRY_FILENAME
    if not path.exists():
        return {"active": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"active": {}}

    if not isinstance(data, dict):
        return {"active": {}}
    if not isinstance(data.get("active"), dict):
        data["active"] = {}

    return data


def write_model_registry(registry: dict[str, Any]) -> None:
    output_dir = station_model_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MODEL_REGISTRY_FILENAME
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _station_model_path(
    *,
    station_code: str,
    variable_code: int,
    model_name: str,
    trained_at: datetime,
) -> Path:
    output_dir = station_model_dir()
    timestamp = trained_at.strftime("%Y%m%dT%H%M%SZ")
    filename = f"{_slug(station_code)}_{variable_code}_{_slug(model_name)}_{timestamp}.joblib"
    return output_dir / filename


def _active_key(station_code: str, variable_code: int) -> str:
    return f"{station_code}:{variable_code}"


def _safe_model_path(model_id: str) -> Path:
    if "/" in model_id or "\\" in model_id or model_id in {"", ".", ".."}:
        raise ValueError("Invalid model id")
    if not model_id.endswith(".joblib"):
        raise ValueError("Invalid model id")

    output_dir = station_model_dir().resolve()
    path = (output_dir / model_id).resolve()

    if path.parent != output_dir:
        raise ValueError("Invalid model id")

    return path


def _model_summary(
    path: Path,
    registry: dict[str, Any],
    *,
    include_features: bool = False,
) -> dict[str, Any]:
    stat = path.stat()
    summary: dict[str, Any] = {
        "id": path.name,
        "model_path": str(path),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "active": False,
    }

    try:
        payload = joblib.load(path)
    except Exception as exc:
        summary["load_error"] = str(exc)
        return summary

    station_code = payload.get("station_code")
    variable_code = payload.get("variable_code")
    active_key = None

    if station_code and variable_code is not None:
        active_key = _active_key(str(station_code), int(variable_code))

    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    summary.update(
        {
            "station_code": station_code,
            "station_name": payload.get("station_name"),
            "variable_code": variable_code,
            "variable_name": payload.get("variable_name"),
            "target_variable": payload.get("target_variable"),
            "model_name": payload.get("model_name"),
            "date_from": payload.get("date_from"),
            "date_to": payload.get("date_to"),
            "rows": payload.get("rows"),
            "training_rows": payload.get("training_rows"),
            "evaluation_rows": payload.get("evaluation_rows"),
            "evaluation": payload.get("evaluation"),
            "metrics": metrics,
            "trained_at": payload.get("trained_at"),
            "active": bool(active_key and registry.get("active", {}).get(active_key) == path.name),
        }
    )

    if include_features:
        summary["feature_order"] = payload.get("feature_order") or []

    return summary
