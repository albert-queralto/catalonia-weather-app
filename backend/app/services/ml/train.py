import os
import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import io
from datetime import datetime, timezone
from app.services.ml.storage import save_model_to_db_sync

API_URL = "http://api:4000/api/v1/meteocat"

MODEL_REGISTRY = {
    "random_forest": RandomForestRegressor,
    "linear_regression": LinearRegression,
    "decision_tree": DecisionTreeRegressor,
    "xgboost": XGBRegressor,
}

def fetch_station_variables(station_code):
    resp = requests.get(f"{API_URL}/station/{station_code}/variables")
    return resp.json()

def fetch_variable_values(station_code, variable_id, date_from, date_to):
    resp = requests.get(
        f"{API_URL}/station/{station_code}/variable/{variable_id}/values",
        params={"date_from": date_from, "date_to": date_to}
    )
    return resp.json()

def fetch_all_stations():
    resp = requests.get(f"{API_URL}/stations")
    return resp.json()

def build_training_dataframe(station_code, date_from, date_to, target_variable="Precipitació"):
    variables = fetch_station_variables(station_code)
    dfs = []
    var_names = []
    for var in variables:
        var_id = var["codi"]
        var_name = var["nom"]
        values = fetch_variable_values(station_code, var_id, date_from, date_to)
        df = pd.DataFrame(values)
        if not df.empty:
            df = df.rename(columns={"value": var_name})
            if "date" in df.columns and var_name in df.columns:
                df = df[["date", var_name]]
                dfs.append(df)
                var_names.append(var_name)
    if not dfs:
        return pd.DataFrame(), []
    df_merged = dfs[0]
    for df in dfs[1:]:
        df_merged = pd.merge(df_merged, df, on="date", how="outer")
    df_merged = df_merged.sort_values("date").dropna()
    return df_merged, var_names

def train_and_save_model(
    station_code, 
    date_from, 
    date_to,
    target_variable="Precipitació", 
    model_name="xgboost",
    session=None
):
    df, var_names = build_training_dataframe(station_code, date_from, date_to, target_variable)
    if df.empty:
        print(f"[SKIP] No data for station {station_code} in range {date_from} to {date_to}")
        return None
    if target_variable not in df.columns:
        print(f"[SKIP] Target variable '{target_variable}' not found for station {station_code}")
        return None

    # Feature engineering: drop date, target, and any non-numeric columns
    feature_cols = [col for col in df.columns if col not in ("date", target_variable)]
    X = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    y = df[target_variable].astype(float)

    # Model selection
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Model '{model_name}' not supported. Choose from: {list(MODEL_REGISTRY.keys())}")
    model_cls = MODEL_REGISTRY[model_name]
    model = model_cls()
    model.fit(X, y)

    # Evaluation
    y_pred = model.predict(X)
    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y, y_pred))),
        "r2": float(r2_score(y, y_pred)),
        "n_samples": int(len(y)),
    }

    # Serialize model
    buf = io.BytesIO()
    joblib.dump(model, buf)
    model_bytes = buf.getvalue()

    # Save to DB
    if session is not None:
        save_model_to_db_sync(
            station_code=station_code,
            model_name=model_name,
            model_bytes=model_bytes,
            session=session,
            features=feature_cols,
            target=target_variable,
            metrics=metrics,
            model_version="1.0",
            trained_at=datetime.now(timezone.utc),
        )
        print(f"[TRAINED] Model for {station_code} ({model_name}) saved to DB. Metrics: {metrics}")
        return f"Model for {station_code} ({model_name}) saved to DB"
    else:
        # fallback: save to disk if no session provided
        os.makedirs("models", exist_ok=True)
        model_path = f"models/model_{station_code}_{model_name}.joblib"
        joblib.dump(model, model_path)
        print(f"[TRAINED] Model for {station_code} ({model_name}) saved to disk. Metrics: {metrics}")
        return model_path

def get_available_models():
    return list(MODEL_REGISTRY.keys())