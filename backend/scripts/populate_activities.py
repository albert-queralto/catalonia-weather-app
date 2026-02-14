"""
Generate synthetic activities and user interactions for testing the recommender system.

Usage:
    python scripts/populate_activities.py --activities 100 --users 10 --interactions 500
"""
import argparse
import os
import sys
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.models import ActivitySuggestion, Event, User
from app.core.security import get_password_hash

# ============================================================================
# CONFIGURATION
# ============================================================================

# Categories (must match your database)
CATEGORIES = ["Sport", "Culture", "Nature", "Food", "Leisure", "Other"]

# Activity name templates by category
ACTIVITY_NAMES = {
    "Sport": [
        "Beach Volleyball Court", "Mountain Biking Trail", "Rock Climbing Wall",
        "Kayaking River Route", "Tennis Courts", "Hiking Path", "Swimming Pool",
        "Skateboard Park", "CrossFit Gym", "Yoga Studio", "Running Track",
        "Surf Spot", "Paddle Surf Location", "Basketball Court", "Football Field"
    ],
    "Culture": [
        "Art Gallery", "History Museum", "Contemporary Art Center", "Theater",
        "Concert Hall", "Cultural Center", "Archaeological Site", "Library",
        "Cinema", "Opera House", "Street Art Tour", "Photography Exhibition",
        "Sculpture Park", "Literary Cafe", "Jazz Club"
    ],
    "Nature": [
        "Botanical Garden", "Nature Reserve", "Wildlife Sanctuary", "Forest Trail",
        "Waterfall Viewpoint", "Beach", "Mountain Summit", "Lake", "Natural Park",
        "Bird Watching Spot", "Scenic Overlook", "Caves", "Coastal Path",
        "River Walk", "Desert Trail"
    ],
    "Food": [
        "Local Market", "Wine Tasting", "Cooking Class", "Food Tour",
        "Traditional Restaurant", "Tapas Bar", "Cheese Factory", "Olive Oil Mill",
        "Seafood Restaurant", "Vegetarian Cafe", "Street Food Market",
        "Bakery Workshop", "Brewery Tour", "Farm-to-Table Restaurant", "Picnic Area"
    ],
    "Leisure": [
        "Shopping District", "Amusement Park", "Escape Room", "Gaming Arcade",
        "Spa & Wellness", "Botanical Garden Walk", "City Park", "Boat Ride",
        "Horse Riding", "Fishing Spot", "Mini Golf", "Bowling Alley",
        "Zoo", "Aquarium", "Adventure Park"
    ],
    "Other": [
        "Tourist Information Center", "Viewpoint", "Photo Spot", "Marketplace",
        "Flea Market", "Craft Workshop", "Community Center", "Co-working Space",
        "Public Square", "Promenade", "Observatory", "Church", "Castle",
        "Bridge Lookout", "Harbor"
    ]
}

# Tags by category
TAGS_BY_CATEGORY = {
    "Sport": ["outdoor", "fitness", "team", "water", "extreme", "beginner-friendly", "family"],
    "Culture": ["indoor", "art", "history", "music", "educational", "family", "evening"],
    "Nature": ["outdoor", "scenic", "hiking", "wildlife", "photography", "peaceful", "family"],
    "Food": ["local", "traditional", "gourmet", "vegetarian", "wine", "budget-friendly", "family"],
    "Leisure": ["fun", "relaxing", "family", "indoor", "outdoor", "romantic", "group"],
    "Other": ["sightseeing", "historic", "free", "accessible", "popular", "instagram"]
}

# Catalunya region bounds (approximate)
CATALUNYA_BOUNDS = {
    "lat_min": 40.5,
    "lat_max": 42.9,
    "lon_min": 0.2,
    "lon_max": 3.3
}

# Barcelona area (for more concentrated activities)
BARCELONA_AREA = {
    "lat": 41.3851,
    "lon": 2.1734,
    "radius_km": 20
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def random_location(concentrate_in_barcelona=0.7):
    """Generate a random location, with bias towards Barcelona."""
    if random.random() < concentrate_in_barcelona:
        # Generate near Barcelona
        angle = random.uniform(0, 2 * 3.14159)
        radius_km = random.uniform(0, BARCELONA_AREA["radius_km"])
        # Rough conversion: 1 degree lat ~ 111km, 1 degree lon ~ 111km * cos(lat)
        lat_offset = (radius_km / 111.0) * random.choice([-1, 1])
        lon_offset = (radius_km / (111.0 * 0.75)) * random.choice([-1, 1])
        lat = BARCELONA_AREA["lat"] + lat_offset
        lon = BARCELONA_AREA["lon"] + lon_offset
    else:
        # Random location in Catalunya
        lat = random.uniform(CATALUNYA_BOUNDS["lat_min"], CATALUNYA_BOUNDS["lat_max"])
        lon = random.uniform(CATALUNYA_BOUNDS["lon_min"], CATALUNYA_BOUNDS["lon_max"])
    
    return round(lat, 6), round(lon, 6)


def random_activity_attributes(category):
    """Generate random attributes for an activity."""
    names = ACTIVITY_NAMES.get(category, ["Activity"])
    name = random.choice(names)
    
    # Add location descriptor sometimes
    descriptors = ["North", "South", "East", "West", "Central", "Urban", "Historic"]
    if random.random() < 0.4:
        name = f"{random.choice(descriptors)} {name}"
    
    # Tags: 2-5 random tags from category
    available_tags = TAGS_BY_CATEGORY.get(category, ["general"])
    num_tags = random.randint(2, min(5, len(available_tags)))
    tags = random.sample(available_tags, num_tags)
    
    # Indoor/covered likelihood varies by category
    indoor_prob = {
        "Sport": 0.3,
        "Culture": 0.7,
        "Nature": 0.05,
        "Food": 0.6,
        "Leisure": 0.5,
        "Other": 0.4
    }.get(category, 0.3)
    
    indoor = random.random() < indoor_prob
    covered = indoor or (random.random() < 0.2)  # Some outdoor activities are covered
    
    # Price level: 0-4 (0=free, 4=expensive)
    price_level = random.choices([0, 1, 2, 3, 4], weights=[20, 35, 25, 15, 5])[0]
    
    # Difficulty: 0-4 (0=very easy, 4=expert)
    difficulty = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
    
    # Duration in minutes
    duration_options = [30, 60, 90, 120, 180, 240, 300, 360, 480]
    duration_minutes = random.choice(duration_options)
    
    return {
        "name": name,
        "tags": tags,
        "indoor": indoor,
        "covered": covered,
        "price_level": price_level,
        "difficulty": difficulty,
        "duration_minutes": duration_minutes
    }


def create_test_user(session, index, is_admin=False):
    """Create a test user."""
    user_id = str(uuid.uuid4())
    email = f"test_user_{index}@example.com" if not is_admin else f"admin{index}@example.com"
    
    user = User(
        id=user_id,
        email=email,
        password_hash=get_password_hash("password123"),
        role="admin" if is_admin else "user",
        is_active=True,
        email_verified=True
    )
    session.add(user)
    return user


def generate_activities(session, count=100):
    """Generate synthetic activities."""
    print(f"\n{'='*60}")
    print(f"Generating {count} activities...")
    print(f"{'='*60}\n")
    
    activities = []
    
    for i in range(count):
        category = random.choice(CATEGORIES)
        attrs = random_activity_attributes(category)
        lat, lon = random_location()
        
        activity = ActivitySuggestion(
            id=str(uuid.uuid4()),
            name=attrs["name"],
            category=category,
            tags=attrs["tags"],
            indoor=attrs["indoor"],
            covered=attrs["covered"],
            price_level=attrs["price_level"],
            difficulty=attrs["difficulty"],
            duration_minutes=attrs["duration_minutes"],
            location=f"SRID=4326;POINT({lon} {lat})",
            validated=random.random() < 0.8,  # 80% validated
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))
        )
        
        session.add(activity)
        activities.append(activity)
        
        if (i + 1) % 20 == 0:
            print(f"  Created {i + 1}/{count} activities...")
    
    session.commit()
    print(f"\n✅ Created {len(activities)} activities")
    
    # Print summary by category
    category_counts = {}
    for act in activities:
        category_counts[act.category] = category_counts.get(act.category, 0) + 1
    
    print(f"\nBreakdown by category:")
    for cat, cnt in sorted(category_counts.items()):
        print(f"  {cat:12s}: {cnt:3d}")
    
    return activities


def generate_user_preferences(session, users):
    """Generate user preferences for categories."""
    print(f"\n{'='*60}")
    print(f"Generating user preferences...")
    print(f"{'='*60}\n")
    
    for user in users:
        # Each user has preferences for 3-5 categories
        num_prefs = random.randint(3, 5)
        preferred_categories = random.sample(CATEGORIES, num_prefs)
        
        for cat in preferred_categories:
            weight = random.uniform(0.3, 1.0)
            session.execute(
                text("""
                    INSERT INTO user_preferences (user_id, category, weight)
                    VALUES (:user_id, :category, :weight)
                    ON CONFLICT (user_id, category) DO UPDATE SET weight = EXCLUDED.weight
                """),
                {"user_id": str(user.id), "category": cat, "weight": weight}
            )
    
    session.commit()
    print(f"✅ Created preferences for {len(users)} users")


def generate_interactions(session, users, activities, count=500):
    """Generate synthetic user interactions (views, clicks, saves, ratings)."""
    print(f"\n{'='*60}")
    print(f"Generating {count} user interactions...")
    print(f"{'='*60}\n")
    
    event_types = ["view", "click", "save", "complete", "rate"]
    event_weights = [60, 20, 10, 5, 5]  # Views are most common
    
    interactions = []
    
    for i in range(count):
        user = random.choice(users)
        activity = random.choice(activities)
        
        # Simulate a session with related events
        request_id = str(uuid.uuid4())
        session_time = datetime.now(timezone.utc) - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # User location (somewhere near Barcelona mostly)
        user_lat, user_lon = random_location(concentrate_in_barcelona=0.9)
        
        # Weather context (random but realistic)
        weather_temp_c = random.uniform(5, 35)
        weather_precip_prob = random.uniform(0, 100)
        weather_wind_kmh = random.uniform(0, 50)
        weather_is_day = 1.0 if 7 <= session_time.hour <= 20 else 0.0
        
        # Create view event
        view_event = Event(
            id=str(uuid.uuid4()),
            user_id=user.id,
            activity_id=activity.id,
            event_type="view",
            ts=session_time,
            request_id=request_id,
            position=random.randint(0, 19),
            user_lat=user_lat,
            user_lon=user_lon,
            weather_temp_c=weather_temp_c,
            weather_precip_prob=weather_precip_prob,
            weather_wind_kmh=weather_wind_kmh,
            weather_is_day=weather_is_day,
            rating=None
        )
        session.add(view_event)
        interactions.append(view_event)
        
        # Sometimes follow up with click/save/complete/rate
        if random.random() < 0.3:  # 30% chance of engagement
            engagement_type = random.choices(
                ["click", "save", "complete", "rate"],
                weights=[50, 25, 15, 10]
            )[0]
            
            engagement_event = Event(
                id=str(uuid.uuid4()),
                user_id=user.id,
                activity_id=activity.id,
                event_type=engagement_type,
                ts=session_time + timedelta(seconds=random.randint(5, 300)),
                request_id=request_id,
                position=None,
                user_lat=user_lat,
                user_lon=user_lon,
                weather_temp_c=weather_temp_c,
                weather_precip_prob=weather_precip_prob,
                weather_wind_kmh=weather_wind_kmh,
                weather_is_day=weather_is_day,
                rating=random.randint(1, 5) if engagement_type == "rate" else None
            )
            session.add(engagement_event)
            interactions.append(engagement_event)
        
        if (i + 1) % 100 == 0:
            print(f"  Created {i + 1}/{count} interaction sessions...")
            session.commit()
    
    session.commit()
    print(f"\n✅ Created {len(interactions)} total events")
    
    # Print summary
    event_counts = {}
    for event in interactions:
        event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
    
    print(f"\nBreakdown by event type:")
    for etype, cnt in sorted(event_counts.items()):
        print(f"  {etype:12s}: {cnt:3d}")
    
    ratings = [e for e in interactions if e.rating is not None]
    if ratings:
        avg_rating = sum(e.rating for e in ratings) / len(ratings)
        print(f"\nRatings: {len(ratings)} total, avg={avg_rating:.2f}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Populate database with synthetic activity data")
    parser.add_argument("--activities", type=int, default=100, help="Number of activities to create")
    parser.add_argument("--users", type=int, default=10, help="Number of test users to create")
    parser.add_argument("--interactions", type=int, default=500, help="Number of interaction sessions")
    parser.add_argument("--clear", action="store_true", help="Clear existing data first")
    
    args = parser.parse_args()
    
    # Get database URL from environment
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        if args.clear:
            print("\n⚠️  Clearing existing data...")
            session.execute(text("DELETE FROM events"))
            session.execute(text("DELETE FROM user_preferences"))
            session.execute(text("DELETE FROM activities"))
            session.execute(text("DELETE FROM users WHERE email LIKE 'test_user_%' OR email LIKE 'admin%'"))
            session.commit()
            print("✅ Cleared existing test data\n")
        
        # Create test users
        print(f"\n{'='*60}")
        print(f"Creating {args.users} test users...")
        print(f"{'='*60}\n")
        
        users = []
        for i in range(args.users):
            user = create_test_user(session, i, is_admin=(i == 0))
            users.append(user)
        
        session.commit()
        print(f"✅ Created {len(users)} users")
        print(f"   Test credentials: test_user_0@example.com / password123")
        
        # Generate activities
        activities = generate_activities(session, args.activities)
        
        # Generate user preferences
        generate_user_preferences(session, users)
        
        # Generate interactions
        generate_interactions(session, users, activities, args.interactions)
        
        print(f"\n{'='*60}")
        print(f"✅ Population complete!")
        print(f"{'='*60}")
        print(f"\nSummary:")
        print(f"  Users:        {len(users)}")
        print(f"  Activities:   {len(activities)}")
        print(f"  Interactions: ~{args.interactions}")
        print(f"\nYou can now train the model with:")
        print(f"  python app/services/recommender/train_from_db.py")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()