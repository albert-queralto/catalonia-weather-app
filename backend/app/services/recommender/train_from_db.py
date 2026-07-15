import os
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, ndcg_score, average_precision_score
import lightgbm as lgb

from app.services.recommender.feature_contract import (
    FEATURE_COLUMNS,
    assert_feature_columns_present,
)

from app.services.recommender.features import (
    compute_tag_overlap,
    compute_weather_penalties,
    estimate_transport_time_min,
    season_from_month,
    is_ozone_season,
    compute_ozone_penalty,
)

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
    pg_url = os.environ.get("DATABASE_URL")  # e.g. postgresql+psycopg2://postgres:postgres@localhost:5432/activities
    if not pg_url:
        raise SystemExit("Set DATABASE_URL")

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
            e.weather_temp_c, e.weather_precip_prob, e.weather_wind_kmh, e.weather_is_day,
            e.apparent_temp_c,
            e.uv_index,
            e.air_quality_score,
            e.ozone,
            e.alert_severity,
            e.weather_condition,
            e.ranking_strategy,
            e.model_score,
            e.model_confidence,
            e.exploration_bucket,
            e.dismiss_reason,
            e.rating
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
        WHERE event_type IN ('click','save','complete','rate')
          AND ts >= now() - interval '{lookback_days + label_window_days} days'
        """,
        engine,
        parse_dates=["ts"],
    )
    
    if len(outcomes) == 0:
        raise SystemExit("No positive events (click/save) found in the data. Cannot train model.")

    ratings = pd.read_sql(
        f"""
        SELECT
        user_id::text,
        activity_id::text,
        rating,
        ts
        FROM events
        WHERE rating IS NOT NULL
        AND ts >= now() - interval '{lookback_days + label_window_days} days'
        """,
        engine,
        parse_dates=["ts"],
    )

    # 2b) Load user engagement history
    user_stats = pd.read_sql(
        f"""
        SELECT 
            user_id::text,
            COUNT(*) as total_events,
            COUNT(DISTINCT activity_id) as unique_activities,
            AVG(CASE WHEN rating IS NOT NULL THEN rating END) as user_avg_rating,
            COUNT(CASE WHEN event_type IN ('click','save','complete') THEN 1 END) as user_engagement_count
        FROM events
        WHERE ts >= now() - interval '{lookback_days + label_window_days} days'
        GROUP BY user_id
        """,
        engine,
    )

    # 2c) Load activity popularity stats
    activity_stats = pd.read_sql(
        f"""
        SELECT 
            activity_id::text,
            COUNT(CASE WHEN event_type = 'view' THEN 1 END) as activity_view_count,
            AVG(CASE WHEN rating IS NOT NULL THEN rating END) as activity_avg_rating,
            COUNT(CASE WHEN event_type IN ('click','save','complete') THEN 1 END) as activity_engagement_count
        FROM events
        WHERE ts >= now() - interval '{lookback_days + label_window_days} days'
        GROUP BY activity_id
        """,
        engine,
    )

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
            "apparent_temp_c": "first",
            "uv_index": "first",
            "air_quality_score": "first",
            "ozone": "first",
            "alert_severity": "first",
            "weather_condition": "first",
            "ranking_strategy": "first",
            "model_score": "first",
            "model_confidence": "first",
            "exploration_bucket": "first",
            "dismiss_reason": "first",
            "rating": "first",
            "is_pos": "max",
        })
        .rename(columns={"is_pos": "label"})
    )
    
    labeled = labeled.merge(
        ratings[["user_id", "activity_id", "rating"]],
        on=["user_id", "activity_id"],
        how="left",
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

    # Merge user statistics
    df = df.merge(user_stats, on="user_id", how="left")
    
    # Merge activity statistics
    df = df.merge(activity_stats, on="activity_id", how="left")
    
    # Fill missing values for new users/activities (cold start)
    df['total_events'] = df['total_events'].fillna(0)
    df['unique_activities'] = df['unique_activities'].fillna(0)
    df['user_avg_rating'] = df['user_avg_rating'].fillna(2.5)  # Neutral default
    df['user_engagement_count'] = df['user_engagement_count'].fillna(0)
    df['activity_view_count'] = df['activity_view_count'].fillna(0)
    df['activity_avg_rating'] = df['activity_avg_rating'].fillna(2.5)
    df['activity_engagement_count'] = df['activity_engagement_count'].fillna(0)
    df["apparent_temp_c"] = df["apparent_temp_c"].fillna(df["weather_temp_c"])
    df["uv_index"] = df["uv_index"].fillna(0.0)
    df["air_quality_score"] = df["air_quality_score"].fillna(0.0)
    df["ozone"] = df["ozone"].fillna(0.0)
    df["alert_severity"] = df["alert_severity"].fillna(0.0)
    df["weather_condition"] = df["weather_condition"].fillna("unknown")
    df["ranking_strategy"] = df["ranking_strategy"].fillna("default")
    df["model_score"] = df["model_score"].fillna(0.0)
    df["model_confidence"] = df["model_confidence"].fillna(0.0)
    df["exploration_bucket"] = df["exploration_bucket"].fillna("default")
    df["dismiss_reason"] = df["dismiss_reason"].fillna("unknown")

    # Derived features
    df['activity_engagement_rate'] = df['activity_engagement_count'] / (df['activity_view_count'] + 1)
    df['user_exploration_rate'] = df['unique_activities'] / (df['total_events'] + 1)

    # 5) Load user preference weights by category
    df['total_events'] = df['total_events'].fillna(0)
    df['unique_activities'] = df['unique_activities'].fillna(0)
    df['user_avg_rating'] = df['user_avg_rating'].fillna(2.5)  # Neutral default
    df['user_engagement_count'] = df['user_engagement_count'].fillna(0)
    df['activity_view_count'] = df['activity_view_count'].fillna(0)
    df['activity_avg_rating'] = df['activity_avg_rating'].fillna(2.5)
    df['activity_engagement_count'] = df['activity_engagement_count'].fillna(0)
    
    df['activity_engagement_rate'] = df['activity_engagement_count'] / (df['activity_view_count'] + 1)
    df['user_exploration_rate'] = df['unique_activities'] / (df['total_events'] + 1)

    df["month"] = df["impression_ts"].dt.month
    df["season"] = df["month"].apply(lambda m: season_from_month(int(m)))
    df["is_evening"] = df["impression_ts"].dt.hour.between(18, 23).astype(float)
    df["is_school_holiday"] = 0.0
    df["is_open_now"] = 1.0

    df["user_avg_completed_duration"] = df.get("user_avg_completed_duration", 60.0)
    df["user_bad_weather_dismiss_rate"] = df.get("user_bad_weather_dismiss_rate", 0.0)

    df["ozone_season"] = df["month"].apply(lambda m: 1.0 if is_ozone_season(int(m)) else 0.0)

    df["ozone_penalty"] = df.apply(
        lambda row: compute_ozone_penalty(
            indoor=bool(row["indoor"]),
            ozone=float(row["ozone"] or 0.0),
            month=int(row["month"]),
            hour=int(row["impression_ts"].hour),
        ),
        axis=1,
    )
    
    # Some runtime features may not be available in historical training data yet.
    # Create missing feature columns with safe defaults before selecting FEATURE_COLUMNS.
    if "activity_weather_view_count" not in df.columns:
        df["activity_weather_view_count"] = 0.0

    if "activity_weather_engagement_rate" not in df.columns:
        df["activity_weather_engagement_rate"] = 0.0
        
    prefs = pd.read_sql(
        """
        SELECT user_id::text, category, weight
        FROM user_preferences
        """,
        engine,
    )
    user_cat = prefs.pivot_table(index="user_id", columns="category", values="weight", fill_value=0.0)

    # 6) Feature engineering
    user_tag_events = pd.read_sql(
        f"""
        SELECT
            e.user_id::text AS user_id,
            unnest(a.tags) AS tag,
            COUNT(*) AS cnt
        FROM events e
        JOIN activities a ON e.activity_id = a.id
        WHERE e.event_type IN ('save','complete')
          AND e.ts >= now() - interval '{lookback_days + label_window_days} days'
        GROUP BY 1, 2
        """,
        engine,
    )
    user_tag_pref_map = {}
    for row in user_tag_events.itertuples(index=False):
        user_tag_pref_map.setdefault(row.user_id, {})[row.tag] = float(row.cnt)
    
    df["distance_km"] = haversine_km(df["user_lat"], df["user_lon"], df["lat"], df["lon"])
    df["transport_time_min"] = df["distance_km"].apply(
        lambda d: estimate_transport_time_min(float(d), "walking")
    )

    def get_cat_weight(row) -> float:
        uid = row["user_id"]
        cat = row["category"]
        if uid in user_cat.index and cat in user_cat.columns:
            return float(user_cat.loc[uid, cat])
        return 0.0

    df["cat_weight"] = df.apply(get_cat_weight, axis=1)

    # Minimal tag features
    # Here: tag_overlap based on whether any tag string exists
    df["tag_overlap"] = df.apply(
        lambda row: compute_tag_overlap(
            row['tags'] if isinstance(row['tags'], list) else [],
            user_tag_pref_map.get(row['user_id'], {}),
        ),
        axis=1,
    )

    df["indoor_f"] = df["indoor"].astype(float)
    df["covered_f"] = df["covered"].astype(float)
    df["price_level_f"] = df["price_level"].astype(float)
    df["difficulty_f"] = df["difficulty"].astype(float)
    df["duration_minutes_f"] = df["duration_minutes"].astype(float)
    
    df["outdoor_aq_risk"] = (1.0 - df["indoor_f"]) * df["air_quality_score"]
    df["outdoor_uv_risk"] = (1.0 - df["indoor_f"]) * df["uv_index"]
    df["outdoor_alert_risk"] = (1.0 - df["indoor_f"]) * df["alert_severity"]

    # Weather-derived penalties for outdoor activities
    penalties = df.apply(
        lambda row: compute_weather_penalties(
            indoor=row["indoor"],
            covered=row["covered"],
            weather_temp_c=row["weather_temp_c"],
            weather_precip_prob=row["weather_precip_prob"],
            weather_wind_kmh=row["weather_wind_kmh"],
        ),
        axis=1,
    )
    df["precip_penalty"] = penalties.apply(lambda x: x.precip_penalty)
    df['wind_penalty'] = penalties.apply(lambda x: x.wind_penalty)
    df['cold_penalty'] = penalties.apply(lambda x: x.cold_penalty)
    df['heat_penalty'] = penalties.apply(lambda x: x.heat_penalty)
    
    df['hour_of_day'] = df['impression_ts'].dt.hour
    df['day_of_week'] = df['impression_ts'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5,6]).astype(float)
    
    df['temp_distance_interaction'] = df['weather_temp_c'] * df['distance_km']
    df['price_distance_interaction'] = df['price_level_f'] * df['distance_km']
    df['cat_weight_distance'] = df['cat_weight'] * df['distance_km']
    df['indoor_precip'] = df['indoor_f'] * df['weather_precip_prob']

    # Row-level explicit rating is optional.
    # Keep missing values as NaN so implicit labels still work.
    if "rating" not in df.columns:
        rating_candidates = [
            c for c in df.columns
            if c in ("rating_x", "rating_y") or c.startswith("rating_")
        ]

        if rating_candidates:
            rating_values = df[rating_candidates].apply(
                lambda col: pd.to_numeric(col, errors="coerce")
            )
            df["rating"] = rating_values.bfill(axis=1).iloc[:, 0]
        else:
            df["rating"] = np.nan
    else:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    if "label" not in df.columns:
        df["label"] = 0

    # Ensure no nulls
    X = df[FEATURE_COLUMNS].fillna(0.0)
    
    # Combine explicit ratings with implicit signals
    assert_feature_columns_present(X.columns)
    
    def create_composite_label(row):
        # Explicit rating takes precedence (strongest signal)
        if pd.notna(row['rating']):
            return 1 if row['rating'] >= 3 else 0
        # Fall back to implicit engagement signal
        return int(row['label'])
    
    y = df.apply(create_composite_label, axis=1)

    # Print label distribution for debugging
    print(f"\n{'='*60}")
    print(f"Label Distribution:")
    print(f"  Total samples:     {len(y)}")
    print(f"  Positive (label=1): {y.sum()} ({100*y.mean():.2f}%)")
    print(f"  Negative (label=0): {(1-y).sum()} ({100*(1-y.mean()):.2f}%)")
    print(f"  Has ratings:       {df['rating'].notna().sum()}")
    print(f"  Has implicit:      {df['label'].sum()}")
    print(f"{'='*60}\n")

    # Safety check: Ensure we have enough positive samples
    if y.sum() < 10:
        raise SystemExit(
            f"Not enough positive samples to train: {y.sum()} positive labels. "
            f"Need at least 10. Consider:\n"
            f"  1. Reducing LOOKBACK_DAYS\n"
            f"  2. Generating more user interactions\n"
            f"  3. Checking if events are being logged correctly"
        )

    # Check if we have variance in features
    if X.std().min() == 0:
        zero_var_features = X.columns[X.std() == 0].tolist()
        print(f"⚠️  Warning: Zero-variance features detected: {zero_var_features}")
        print(f"   These features will not help the model.\n")

    # 7) Train/test split with safety for small datasets
    try:
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
    except ValueError as e:
        # If stratification fails (too few samples in a class), don't stratify
        print(f"⚠️  Cannot stratify split: {e}")
        print("   Using random split instead.\n")
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=None
        )
        
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    # Handle imbalance
    try:
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
        )
    except ValueError as e:
        print(f"⚠️  Cannot stratify validation/test split: {e}")
        print("   Using random split instead.\n")
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42, stratify=None
        )
    
    pos = y_train.sum()
    neg = len(y_train) - pos
    if pos == 0:
        raise SystemExit("No positive events in training data. Cannot train model.")
    scale_pos_weight = (neg / max(pos, 1))

    # Adjust hyperparameters based on dataset size
    n_samples = len(X_train)
    if n_samples < 500:
        # Very small dataset - use shallow trees
        n_estimators = 100
        num_leaves = 7
        min_child_samples = 5
    elif n_samples < 2000:
        # Small dataset
        n_estimators = 300
        num_leaves = 15
        min_child_samples = 10
    else:
        # Larger dataset
        n_estimators = 800
        num_leaves = 31
        min_child_samples = 20

    print(f"Model Configuration:")
    print(f"  n_estimators:      {n_estimators}")
    print(f"  num_leaves:        {num_leaves}")
    print(f"  min_child_samples: {min_child_samples}")
    print(f"  scale_pos_weight:  {scale_pos_weight:.2f}")
    print()

    model = lgb.LGBMClassifier(
        n_estimators=n_estimators,
        learning_rate=0.05,
        num_leaves=num_leaves,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=min_child_samples,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        scale_pos_weight=scale_pos_weight,
        class_weight='balanced',
        min_split_gain=0.0,
        verbose=-1
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric='auc',
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)]
    )

    def evaluate_ranking_metrics(X_data, y_data, model_obj, df_subset):
        """Compute AUC, AP, and NDCG for ranking evaluation"""
        y_pred = model_obj.predict_proba(X_data)[:, 1]
        
        # Overall metrics
        auc = roc_auc_score(y_data, y_pred)
        ap = average_precision_score(y_data, y_pred)
        
        # Ranking metrics per request
        df_subset = df_subset.copy()
        df_subset['pred_score'] = y_pred
        df_subset['true_label'] = y_data.values
        
        ndcg_scores = []
        for req_id in df_subset['request_id'].dropna().unique():
            subset = df_subset[df_subset['request_id'] == req_id]
            if len(subset) > 1 and subset['true_label'].sum() > 0:
                try:
                    ndcg = ndcg_score(
                        [subset['true_label'].values],
                        [subset['pred_score'].values],
                        k=10
                    )
                    ndcg_scores.append(ndcg)
                except Exception:
                    pass
        
        avg_ndcg = np.mean(ndcg_scores) if ndcg_scores else 0.0
        return auc, ap, avg_ndcg
    
    # Get test indices to match with df
    test_indices = X_test.index
    df_test = df.loc[test_indices]
    
    auc, ap, avg_ndcg = evaluate_ranking_metrics(X_test, y_test, model, df_test)
    
    print("=" * 60)
    print("Model Performance:")
    print(f"  AUC:        {auc:.4f}")
    print(f"  AP:         {ap:.4f}")
    print(f"  NDCG@10:    {avg_ndcg:.4f}")
    print("=" * 60)
    print("Dataset Stats:")
    print(f"  Train rows: {len(X_train)}")
    print(f"  Val rows:   {len(X_val)}")
    print(f"  Test rows:  {len(X_test)}")
    print(f"  Pos rate:   {y.mean():.4f}")
    print("=" * 60)

    payload = {"model": model, "feature_order": FEATURE_COLUMNS}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump(payload, out_path)
    print(f"Saved model: {out_path}")

if __name__ == "__main__":
    main()
