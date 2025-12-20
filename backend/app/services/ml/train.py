import requests
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor
import joblib
import os
import io
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ml.storage import save_model_to_db


API_URL = "http://localhost:4000/api/v1/meteocat"

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

def build_training_dataframe(station_code, date_from, date_to):
    variables = fetch_station_variables(station_code)
    dfs = []
    for var in variables:
        var_id = var["id"]
        var_name = var["name"]
        values = fetch_variable_values(station_code, var_id, date_from, date_to)
        df = pd.DataFrame(values)
        if not df.empty:
            df = df.rename(columns={"value": var_name})
            df = df[["date", var_name]]
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    df_merged = dfs[0]
    for df in dfs[1:]:
        df_merged = pd.merge(df_merged, df, on="date", how="outer")
    df_merged = df_merged.sort_values("date").dropna()
    return df_merged

async def train_and_save_model(
    station_code, 
    date_from, 
    date_to,
    target_variable="Precipitation", 
    model_name="random_forest",
    session=None
):
    df = build_training_dataframe(station_code, date_from, date_to)
    if df.empty or target_variable not in df.columns:
        raise ValueError("Not enough data or target variable missing")
    X = df.drop(columns=["date", target_variable])
    y = df[target_variable]
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Model '{model_name}' not supported. Choose from: {list(MODEL_REGISTRY.keys())}")
    model_cls = MODEL_REGISTRY[model_name]
    model = model_cls()
    model.fit(X, y)
    # Serialize to bytes
    buf = io.BytesIO()
    joblib.dump(model, buf)
    model_bytes = buf.getvalue()
    # Save to DB using async session
    if session is not None:
        await save_model_to_db(station_code, model_name, model_bytes, session)
        return f"Model for {station_code} ({model_name}) saved to DB"
    else:
        # fallback: save to disk if no session provided
        os.makedirs("models", exist_ok=True)
        model_path = f"models/model_{station_code}_{model_name}.joblib"
        joblib.dump(model, model_path)
        return model_path

def get_available_models():
    return list(MODEL_REGISTRY.keys())