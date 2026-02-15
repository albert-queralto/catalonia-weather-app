from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from app.db.session import get_session
from app.services.user.auth import require_role, get_current_user
from app.db.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/recommendation-performance")
def get_recommendation_performance(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Analyze how well recommendations perform
    Returns CTR, engagement rates, and other metrics
    """
    
    # Overall performance metrics
    overall_stats = db.execute(text(f"""
        WITH impressions AS (
            SELECT request_id, 
                   COUNT(*) as shown,
                   MIN(ts) as session_start
            FROM events
            WHERE event_type = 'view'
              AND ts >= now() - interval '{days} days'
              AND request_id IS NOT NULL
            GROUP BY request_id
        ),
        engagements AS (
            SELECT request_id, 
                   COUNT(*) as engaged,
                   COUNT(CASE WHEN event_type = 'click' THEN 1 END) as clicks,
                   COUNT(CASE WHEN event_type = 'save' THEN 1 END) as saves,
                   COUNT(CASE WHEN event_type = 'complete' THEN 1 END) as completes,
                   AVG(CASE WHEN rating IS NOT NULL THEN rating END) as avg_rating,
                   COUNT(CASE WHEN rating IS NOT NULL THEN 1 END) as rating_count
            FROM events
            WHERE event_type IN ('click', 'save', 'complete', 'rate')
              AND ts >= now() - interval '{days} days'
              AND request_id IS NOT NULL
            GROUP BY request_id
        )
        SELECT 
            COUNT(DISTINCT i.request_id) as total_sessions,
            SUM(i.shown) as total_impressions,
            COALESCE(SUM(e.engaged), 0) as total_engagements,
            COALESCE(SUM(e.clicks), 0) as total_clicks,
            COALESCE(SUM(e.saves), 0) as total_saves,
            COALESCE(SUM(e.completes), 0) as total_completes,
            COALESCE(SUM(e.rating_count), 0) as total_ratings,
            COALESCE(AVG(e.avg_rating), 0) as overall_avg_rating,
            AVG(COALESCE(e.engaged::float / NULLIF(i.shown, 0), 0)) as avg_ctr
        FROM impressions i
        LEFT JOIN engagements e ON i.request_id = e.request_id
    """)).fetchone()
    
    # Daily breakdown
    daily_stats = pd.read_sql(f"""
        WITH daily_impressions AS (
            SELECT DATE(ts) as date,
                   COUNT(DISTINCT request_id) as sessions,
                   COUNT(*) as impressions
            FROM events
            WHERE event_type = 'view'
              AND ts >= now() - interval '{days} days'
            GROUP BY DATE(ts)
        ),
        daily_engagements AS (
            SELECT DATE(ts) as date,
                   COUNT(*) as engagements
            FROM events
            WHERE event_type IN ('click', 'save', 'complete')
              AND ts >= now() - interval '{days} days'
            GROUP BY DATE(ts)
        )
        SELECT 
            i.date,
            i.sessions,
            i.impressions,
            COALESCE(e.engagements, 0) as engagements,
            COALESCE(e.engagements::float / NULLIF(i.impressions, 0), 0) as ctr
        FROM daily_impressions i
        LEFT JOIN daily_engagements e ON i.date = e.date
        ORDER BY i.date
    """, db.bind)
    
    # Category performance
    category_stats = pd.read_sql(f"""
        WITH category_impressions AS (
            SELECT a.category,
                   COUNT(*) as impressions
            FROM events e
            JOIN activities a ON e.activity_id = a.id
            WHERE e.event_type = 'view'
              AND e.ts >= now() - interval '{days} days'
            GROUP BY a.category
        ),
        category_engagements AS (
            SELECT a.category,
                   COUNT(*) as engagements,
                   AVG(CASE WHEN e.rating IS NOT NULL THEN e.rating END) as avg_rating
            FROM events e
            JOIN activities a ON e.activity_id = a.id
            WHERE e.event_type IN ('click', 'save', 'complete', 'rate')
              AND e.ts >= now() - interval '{days} days'
            GROUP BY a.category
        )
        SELECT 
            i.category,
            i.impressions,
            COALESCE(e.engagements, 0) as engagements,
            COALESCE(e.engagements::float / NULLIF(i.impressions, 0), 0) as ctr,
            COALESCE(e.avg_rating, 0) as avg_rating
        FROM category_impressions i
        LEFT JOIN category_engagements e ON i.category = e.category
        ORDER BY i.impressions DESC
    """, db.bind)
    
    # Top performing activities
    top_activities = pd.read_sql(f"""
        WITH activity_impressions AS (
            SELECT e.activity_id,
                   a.name,
                   a.category,
                   COUNT(*) as impressions
            FROM events e
            JOIN activities a ON e.activity_id = a.id
            WHERE e.event_type = 'view'
              AND e.ts >= now() - interval '{days} days'
            GROUP BY e.activity_id, a.name, a.category
        ),
        activity_engagements AS (
            SELECT e.activity_id,
                   COUNT(*) as engagements,
                   AVG(CASE WHEN e.rating IS NOT NULL THEN e.rating END) as avg_rating
            FROM events e
            WHERE e.event_type IN ('click', 'save', 'complete', 'rate')
              AND e.ts >= now() - interval '{days} days'
            GROUP BY e.activity_id
        )
        SELECT 
            i.activity_id,
            i.name,
            i.category,
            i.impressions,
            COALESCE(e.engagements, 0) as engagements,
            COALESCE(e.engagements::float / NULLIF(i.impressions, 0), 0) as ctr,
            COALESCE(e.avg_rating, 0) as avg_rating
        FROM activity_impressions i
        LEFT JOIN activity_engagements e ON i.activity_id = e.activity_id
        WHERE i.impressions >= 5
        ORDER BY ctr DESC, i.impressions DESC
        LIMIT 10
    """, db.bind)
    
    # Position analysis (do higher positions get more engagement?)
    position_stats = pd.read_sql(f"""
        WITH position_impressions AS (
            SELECT position,
                   COUNT(*) as impressions
            FROM events
            WHERE event_type = 'view'
              AND position IS NOT NULL
              AND ts >= now() - interval '{days} days'
            GROUP BY position
        ),
        position_engagements AS (
            SELECT position,
                   COUNT(*) as engagements
            FROM events
            WHERE event_type IN ('click', 'save', 'complete')
              AND position IS NOT NULL
              AND ts >= now() - interval '{days} days'
            GROUP BY position
        )
        SELECT 
            i.position,
            i.impressions,
            COALESCE(e.engagements, 0) as engagements,
            COALESCE(e.engagements::float / NULLIF(i.impressions, 0), 0) as ctr
        FROM position_impressions i
        LEFT JOIN position_engagements e ON i.position = e.position
        ORDER BY i.position
        LIMIT 20
    """, db.bind)
    
    return {
        "overall": {
            "total_sessions": overall_stats[0] or 0,
            "total_impressions": overall_stats[1] or 0,
            "total_engagements": overall_stats[2] or 0,
            "total_clicks": overall_stats[3] or 0,
            "total_saves": overall_stats[4] or 0,
            "total_completes": overall_stats[5] or 0,
            "total_ratings": overall_stats[6] or 0,
            "overall_avg_rating": float(overall_stats[7] or 0),
            "avg_ctr": float(overall_stats[8] or 0),
        },
        "daily": daily_stats.to_dict(orient='records'),
        "by_category": category_stats.to_dict(orient='records'),
        "top_activities": top_activities.to_dict(orient='records'),
        "by_position": position_stats.to_dict(orient='records'),
        "period_days": days
    }


@router.get("/user-engagement")
def get_user_engagement(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """User engagement metrics"""
    
    stats = pd.read_sql(f"""
        SELECT 
            COUNT(DISTINCT user_id) as total_users,
            COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END) as viewing_users,
            COUNT(DISTINCT CASE WHEN event_type IN ('click', 'save', 'complete') THEN user_id END) as engaged_users,
            AVG(user_events) as avg_events_per_user
        FROM (
            SELECT user_id, COUNT(*) as user_events
            FROM events
            WHERE ts >= now() - interval '{days} days'
            GROUP BY user_id
        ) user_counts
    """, db.bind)
    
    return stats.to_dict(orient='records')[0]