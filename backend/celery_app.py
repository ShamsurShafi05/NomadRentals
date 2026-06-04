from celery import Celery

celery_app = Celery(
    "nomadrentals",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["tasks"]
)

celery_app.conf.beat_schedule = {
    "refresh-city-weather-every-6-hours": {
        "task": "tasks.refresh_city_weather",
        "schedule": 21600,  # 6 hours in seconds
        # "schedule": 120,
    }
}

celery_app.conf.timezone = "UTC"