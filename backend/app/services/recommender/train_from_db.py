import os
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, ndcg_score, average_precision_score
import lightgbm as lgb

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
        WHERE event_type IN ('click','save','complete', 'rate')
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
            COUNT(CASE WHEN event_type IN ('save','complete') THEN 1 END) as user_engagement_count
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
            COUNT(*) as activity_view_count,
            AVG(CASE WHEN rating IS NOT NULL THEN rating END) as activity_avg_rating,
            COUNT(CASE WHEN event_type IN ('save','complete') THEN 1 END) as activity_engagement_count
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
    
    # Derived features
    df['activity_engagement_rate'] = df['activity_engagement_count'] / (df['activity_view_count'] + 1)
    df['user_exploration_rate'] = df['unique_activities'] / (df['total_events'] + 1)

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
    
    df['hour_of_day'] = df['impression_ts'].dt.hour
    df['day_of_week'] = df['impression_ts'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(float)

    df['temp_distance_interaction'] = df['weather_temp_c'] * df['distance_km']
    df['price_distance_interaction'] = df['price_level_f'] * df['distance_km']

    df['cat_weight_distance'] = df['cat_weight'] * df['distance_km']
    df['indoor_precip'] = df['indoor_f'] * df['weather_precip_prob']

    feature_cols = [
        # Core features
        "distance_km",
        "cat_weight",
        "tag_overlap",
        
        # Activity attributes
        "indoor_f",
        "covered_f",
        "price_level_f",
        "difficulty_f",
        "duration_minutes_f",
        
        # Weather context
        "weather_temp_c",
        "weather_precip_prob",
        "weather_wind_kmh",
        "weather_is_day",
        
        # Weather penalties
        "precip_penalty",
        "wind_penalty",
        "cold_penalty",
        "heat_penalty",
        
        # Positional
        "position",
        
        # Temporal features
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        
        # Interaction features
        "temp_distance_interaction",
        "price_distance_interaction",
        "cat_weight_distance",
        "indoor_precip",
        
        # User history features
        "total_events",
        "unique_activities",
        "user_avg_rating",
        "user_engagement_count",
        "user_exploration_rate",
        
        # Activity popularity features
        "activity_view_count",
        "activity_avg_rating",
        "activity_engagement_count",
        "activity_engagement_rate",
    ]

    # Ensure no nulls
    X = df[feature_cols].fillna(0.0)
    
    # Combine explicit ratings with implicit signals
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
        for req_id in df_subset['request_id'].unique():
            if pd.isna(req_id):
                continue
            subset = df_subset[df_subset['request_id'] == req_id]
            if len(subset) > 1 and subset['true_label'].sum() > 0:
                try:
                    ndcg = ndcg_score(
                        [subset['true_label'].values],
                        [subset['pred_score'].values],
                        k=10
                    )
                    ndcg_scores.append(ndcg)
                except:
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

    payload = {"model": model, "feature_order": feature_cols}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump(payload, out_path)
    print(f"Saved model: {out_path}")

if __name__ == "__main__":
    main()
