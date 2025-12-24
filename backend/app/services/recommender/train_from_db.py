import os
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    # fast-ish vectorizable implementation for pandas
    R = 6371.0
    lat1 = np.radians(lat1); lon1 = np.radians(lon1)
    lat2 = np.radians(lat2); lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2*np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

def main():
    pg_url = os.environ.get("PG_URL")  # e.g. postgresql+psycopg2://postgres:postgres@localhost:5432/activities
    if not pg_url:
        raise SystemExit("Set PG_URL")

    out_path = os.environ.get("MODEL_OUT", "../models/recommender.joblib")
    lookback_days = int(os.environ.get("LOOKBACK_DAYS", "30"))
    label_window_days = int(os.environ.get("LABEL_WINDOW_DAYS", "7"))
    min_rows = int(os.environ.get("MIN_ROWS", "200"))

    engine = create_engine(pg_url, pool_pre_ping=True)

    # 1) Load impressions (views) with context
    impressions = pd.read_sql(
        f"""
        SELECT
          e.id as impression_id,
          e.user_id::text,
          e.activity_id::text,
          e.ts as impression_ts,
          e.request_id::text,
          e.position,
          e.user_lat, e.user_lon,
          e.weather_temp_c, e.weather_precip_prob, e.weather_wind_kmh, e.weather_is_day
        FROM events e
        WHERE e.event_type='view'
          AND e.ts >= now() - interval '{lookback_days} days'
          AND e.user_lat IS NOT NULL AND e.user_lon IS NOT NULL
          AND e.weather_temp_c IS NOT NULL AND e.weather_precip_prob IS NOT NULL AND e.weather_wind_kmh IS NOT NULL AND e.weather_is_day IS NOT NULL
        """,
        engine,
        parse_dates=["impression_ts"],
    )

    if len(impressions) < min_rows:
        raise SystemExit(f"Not enough impressions to train: {len(impressions)} < {min_rows}")

    # 2) Load outcomes (positives)
    outcomes = pd.read_sql(
        f"""
        SELECT
          user_id::text,
          activity_id::text,
          event_type,
          ts
        FROM events
        WHERE event_type IN ('click','save','complete')
          AND ts >= now() - interval '{lookback_days + label_window_days} days'
        """,
        engine,
        parse_dates=["ts"],
    )
    
    if len(outcomes) == 0:
        raise SystemExit("No positive events (click/save) found in the data. Cannot train model.")

    # 3) Label impressions as positive if an outcome occurs within label window after impression
    # Merge on (user, activity) then check time difference
    merged = impressions.merge(outcomes, on=["user_id", "activity_id"], how="left")
    merged["dt_days"] = (merged["ts"] - merged["impression_ts"]).dt.total_seconds() / 86400.0
    merged["is_pos"] = ((merged["dt_days"] >= 0) & (merged["dt_days"] <= label_window_days)).astype(int)

    # For each impression, if any matching outcome -> label 1
    labeled = (
        merged.groupby(["impression_id"], as_index=False)
        .agg({
            "user_id": "first",
            "activity_id": "first",
            "impression_ts": "first",
            "request_id": "first",
            "position": "first",
            "user_lat": "first",
            "user_lon": "first",
            "weather_temp_c": "first",
            "weather_precip_prob": "first",
            "weather_wind_kmh": "first",
            "weather_is_day": "first",
            "is_pos": "max",
        })
        .rename(columns={"is_pos": "label"})
    )

    # 4) Load activity attributes (including geometry -> lat/lon)
    acts = pd.read_sql(
        """
        SELECT
          id::text AS activity_id,
          category,
          tags,
          indoor,
          covered,
          price_level,
          difficulty,
          duration_minutes,
          ST_Y(location::geometry) AS lat,
          ST_X(location::geometry) AS lon
        FROM activities
        """,
        engine,
    )
    df = labeled.merge(acts, on="activity_id", how="inner")

    # 5) Load user preference weights by category
    prefs = pd.read_sql(
        """
        SELECT user_id::text, category, weight
        FROM user_preferences
        """,
        engine,
    )
    user_cat = prefs.pivot_table(index="user_id", columns="category", values="weight", fill_value=0.0)

    # 6) Feature engineering
    df["distance_km"] = haversine_km(df["user_lat"], df["user_lon"], df["lat"], df["lon"])

    def get_cat_weight(row) -> float:
        uid = row["user_id"]
        cat = row["category"]
        if uid in user_cat.index and cat in user_cat.columns:
            return float(user_cat.loc[uid, cat])
        return 0.0

    df["cat_weight"] = df.apply(get_cat_weight, axis=1)

    # Minimal tag features
    # Here: tag_overlap based on whether any tag string exists
    df["tag_overlap"] = df["tags"].apply(lambda x: float(len(x) if isinstance(x, list) else 0))

    df["indoor_f"] = df["indoor"].astype(float)
    df["covered_f"] = df["covered"].astype(float)
    df["price_level_f"] = df["price_level"].astype(float)
    df["difficulty_f"] = df["difficulty"].astype(float)
    df["duration_minutes_f"] = df["duration_minutes"].astype(float)

    # Weather-derived penalties for outdoor activities
    outdoor = (1.0 - df["indoor_f"])
    df["precip_penalty"] = outdoor * (df["weather_precip_prob"] / 100.0)
    df["wind_penalty"] = outdoor * (df["weather_wind_kmh"] / 50.0)
    df["cold_penalty"] = outdoor * np.maximum(0.0, (10.0 - df["weather_temp_c"]) / 10.0)
    df["heat_penalty"] = outdoor * np.maximum(0.0, (df["weather_temp_c"] - 30.0) / 10.0)

    feature_cols = [
        "distance_km",
        "cat_weight",
        "tag_overlap",
        "indoor_f",
        "covered_f",
        "price_level_f",
        "difficulty_f",
        "duration_minutes_f",
        "weather_temp_c",
        "weather_precip_prob",
        "weather_wind_kmh",
        "weather_is_day",
        "precip_penalty",
        "wind_penalty",
        "cold_penalty",
        "heat_penalty",
        "position",
    ]

    # Ensure no nulls
    X = df[feature_cols].fillna(0.0)
    y = df["label"].astype(int)

    # 7) Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # Handle imbalance
    pos = y_train.sum()
    neg = len(y_train) - pos
    if pos == 0:
        raise SystemExit("No positive events in training data. Cannot train model.")
    scale_pos_weight = (neg / max(pos, 1))

    model = LGBMClassifier(
        n_estimators=800,
        learning_rate=0.03,
        num_leaves=63,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        scale_pos_weight=scale_pos_weight,
    )
    model.fit(X_train, y_train)

    p = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, p)
    print(f"AUC: {auc:.4f} | train_rows={len(X_train)} test_rows={len(X_test)} pos_rate={y.mean():.4f}")

    payload = {"model": model, "feature_order": feature_cols}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump(payload, out_path)
    print(f"Saved model: {out_path}")

if __name__ == "__main__":
    main()
