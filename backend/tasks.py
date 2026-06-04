import asyncio
from celery_app import celery_app
from database import SessionLocal
from models import TrackedCity, City
from services.city_data import fetch_weather

@celery_app.task
def refresh_city_weather():
    """
    Runs every 6 hours via Celery Beat.
    Fetches fresh weather for all tracked cities and updates the DB.
    """
    db = SessionLocal()
    try:
        # Get all unique cities that are being tracked by at least one user
        tracked = db.query(TrackedCity).all()
        city_ids = list(set([t.city_id for t in tracked]))
        
        if not city_ids:
            print("[Celery] No tracked cities found")
            return

        cities = db.query(City).filter(City.id.in_(city_ids)).all()
        print(f"[Celery] Refreshing weather for {len(cities)} cities")

        for city in cities:
            # fetch_weather is async, run it in sync context
            weather = asyncio.run(fetch_weather(city.name))
            
            if weather.get("avg_temp") is not None:
                city.avg_temp = weather["avg_temp"]
                print(f"[Celery] Updated {city.name}: {weather['avg_temp']}°C")
            else:
                print(f"[Celery] Skipped {city.name} — weather fetch failed")

        db.commit()
        print("[Celery] Weather refresh complete")

    except Exception as e:
        print(f"[Celery] Task failed: {e}")
        db.rollback()
    finally:
        db.close()