# NomadRentals API

> Smart city recommendations for remote workers and digital nomads — find your next base based on cost, climate, and your actual work schedule.

---

## What It Does

Most people pick their next city by vibes. NomadRentals scores cities against your real constraints:

- **Can you afford it?** Live cost-of-living data per city, converted to USD
- **Will the weather suit you?** Live temperature from OpenWeatherMap
- **Can you actually work from there?** Timezone overlap calculation — how many of your work hours (e.g. 9–5 UTC+6) fall within reasonable hours in each city

The result is a ranked list of cities with an AI-generated insight for each top match, explaining in plain English why a city does or doesn't fit your lifestyle.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy ORM |
| Caching | Redis (via Memurai on Windows) |
| Background Tasks | Celery + Celery Beat |
| Auth | JWT (python-jose + passlib/bcrypt) |
| External APIs | OpenWeatherMap, Zyla Global City Cost API (RapidAPI), Open Exchange Rates |
| AI Insights | Groq API (Llama 3.1) |
| Async HTTP | httpx |
| Testing | pytest + FastAPI TestClient |

---

## Key Features

### Async API Fan-out
When a city is added, two external API calls fire simultaneously using `asyncio.gather`:
```python
weather_data, col_data = await asyncio.gather(
    fetch_weather(city_name),           # OpenWeatherMap
    fetch_cost_of_living(city_name)     # Zyla via RapidAPI
)
```
Sequential calls would take ~2s. Parallel takes ~700ms.

### Smart Monthly Cost Calculation
Rather than trusting a single "cost of living index", we build a realistic remote worker budget from line items: rent + utilities + transport + internet + phone + food basket. Currency is auto-detected from the API response symbols (€, ฿, £) and converted to USD.

### Redis Caching with TTL
External API responses are cached for 1 hour. Failed/incomplete responses are never cached, preventing stale nulls from persisting.

### Celery Background Tasks
A scheduled task refreshes weather data for all tracked cities every 6 hours — so data is pre-warmed before users ask for it.

### Timezone Overlap Scoring
The recommendation engine's core USP: calculates how many of a user's work hours actually overlap with reasonable working hours (7am–11pm) in each candidate city. Weighted at 40% of the final match score.

### JWT Authentication
Protected routes require a Bearer token. Passwords hashed with bcrypt.

---

## Project Structure

```
backend/
├── main.py               # App entry point, lifespan, router registration
├── database.py           # SQLAlchemy engine + session
├── models.py             # DB models: City, User, UserPreference, TrackedCity
├── schemas.py            # Pydantic schemas for request/response shapes
├── auth.py               # JWT creation, verification, password hashing
├── celery_app.py         # Celery + Beat configuration
├── tasks.py              # Background task: refresh_city_weather
├── routers/
│   ├── cities.py         # City CRUD + recommendation engine
│   ├── users.py          # User CRUD + preferences + city tracking
│   └── auth.py           # Login + /me endpoint
├── services/
│   ├── city_data.py      # Async OWM + Zyla fetchers, currency conversion
│   └── groq_insights.py  # AI insight generation via Groq
└── tests/
    ├── conftest.py
    ├── test_cities.py
    └── test_auth.py
```

---

## API Endpoints

### Cities
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/cities/` | ✅ | List all cities |
| POST | `/cities/` | — | Add city (auto-fetches live data) |
| GET | `/cities/{id}` | — | Get single city |
| PUT | `/cities/{id}` | — | Update city |
| DELETE | `/cities/{id}` | — | Delete city |
| GET | `/cities/recommend?user_id=` | — | Get ranked recommendations with AI insights |

### Users
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/users/` | ✅ | List all users |
| POST | `/users/` | — | Register user |
| GET | `/users/{id}` | — | Get user |
| DELETE | `/users/{id}` | ✅ | Delete user |
| POST | `/users/{id}/preferences` | — | Save preferences |
| GET | `/users/{id}/preferences` | — | Get preferences |
| POST | `/users/{id}/track` | — | Track a city |
| GET | `/users/{id}/tracked` | — | Get tracked cities |

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Get current user from token |

---

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL
- Redis (or Memurai on Windows)

### Installation

```bash
git clone https://github.com/yourusername/NomadRentals.git
cd NomadRentals/backend

python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```
DATABASE_URL=postgresql://username:password@localhost/dbname
OPENWEATHER_API_KEY=your_openweathermap_api_key
RAPIDAPI_KEY=your_rapidapi_key
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=your_secret_key  # generate: python -c "import secrets; print(secrets.token_hex(32))"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Running

```bash
# API server
uvicorn main:app --reload

# Celery worker (separate terminal)
celery -A celery_app worker --loglevel=info --pool=solo

# Celery Beat scheduler (separate terminal)
celery -A celery_app beat --loglevel=info
```

API docs available at `http://localhost:8000/docs`

### Tests

```bash
pytest tests/ -v
```

---

## Recommendation Scoring

Each city is scored against user preferences across three dimensions:

```
Final Score = (temp_match × 30%) + (budget_match × 30%) + (timezone_score × 40%)
```

- **Temp match** — closeness of city avg temp to user's preferred temp
- **Budget match** — whether monthly cost fits within max budget
- **Timezone overlap** — hours of user's workday that fall within 7am–11pm in the city

Top 3 results receive an AI-generated insight from Groq explaining the match in plain English.

---

## Scope of Future Work

- Role-based access control (admin vs user)
- Frontend (React)
- Celery task monitoring via Flower
- Rate limiting middleware
