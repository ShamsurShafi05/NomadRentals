from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import City, UserPreference
from schemas import CityCreate, CityResponse, RecommendationResponse, CityScore
from services.city_data import enrich_city


router = APIRouter(prefix="/cities", tags=["cities"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE a city
# @router.post("/", response_model=CityResponse)
# async def create_city(city: CityCreate, db: Session = Depends(get_db)):
#     new_city = City(**city.model_dump())
#     db.add(new_city)
#     db.commit()
#     db.refresh(new_city)
#     return new_city

@router.post("/", response_model=CityResponse)
async def create_city(city: CityCreate, db: Session = Depends(get_db)):
    # Fetch live data from OWM + Zyla simultaneously
    enriched = await enrich_city(city.name, city.country)
    
    # Merge: client-provided fields + API-fetched fields
    # API fields override whatever the client sent for temp/cost/wifi
    city_data = city.model_dump()
    city_data.update(enriched)
    
    new_city = City(**city_data)
    db.add(new_city)
    db.commit()
    db.refresh(new_city)
    return new_city

# GET all cities
@router.get("/", response_model=list[CityResponse])
async def get_cities(db: Session = Depends(get_db)):
    try:
        cities = db.query(City).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching cities")
    return cities

def calculate_timezone_overlap(client_tz: str, city_tz: str, work_start: int, work_end: int) -> float:
    def parse_offset(tz: str) -> float:
        # handles UTC+6, UTC-5, UTC+5:30 etc
        tz = tz.replace("UTC", "").strip()
        if not tz:
            return 0
        if ":" in tz:
            parts = tz.split(":")
            hours = float(parts[0])
            mins = float(parts[1]) / 60
            return hours + mins if hours >= 0 else hours - mins
        return float(tz)

    client_offset = parse_offset(client_tz)
    city_offset = parse_offset(city_tz)

    # user's work hours in UTC
    work_start_utc = work_start - client_offset
    work_end_utc = work_end - client_offset

    # what time is it in the city during user's work hours
    city_start = work_start_utc + city_offset
    city_end = work_end_utc + city_offset

    # reasonable working hours in city = 7am to 11pm
    reasonable_start = 7
    reasonable_end = 23

    # calculate overlap
    overlap_start = max(city_start, reasonable_start)
    overlap_end = min(city_end, reasonable_end)
    overlap = max(0, overlap_end - overlap_start)

    return overlap


@router.get("/recommend", response_model=RecommendationResponse)
async def recommend_cities(user_id: int, db: Session = Depends(get_db)):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="No preferences found for this user")
    
    cities = db.query(City).all()
    if not cities:
        raise HTTPException(status_code=404, detail="No cities available")

    scored = []
    for city in cities:
        # TEMP SCORE — how close is city temp to preferred temp
        temp_diff = abs((city.avg_temp or 0) - (prefs.preferred_temp or 0))
        temp_match = max(0, 100 - (temp_diff * 10))

        # BUDGET SCORE — is city within budget
        if prefs.max_budget and city.monthly_cost:
            if city.monthly_cost <= prefs.max_budget:
                budget_match = 100
            else:
                over_by = city.monthly_cost - prefs.max_budget
                budget_match = max(0, 100 - (over_by / 10))
        else:
            budget_match = 50

        # TIMEZONE OVERLAP — core USP
        # How many of user's work hours overlap with reasonable hours in city
        timezone_overlap = calculate_timezone_overlap(
            client_tz=prefs.client_timezone or "UTC+0",
            city_tz=city.timezone or "UTC+0",
            work_start=prefs.work_start_hour or 9,
            work_end=prefs.work_end_hour or 17
        )
        timezone_score = (timezone_overlap / 8) * 100

        # FINAL SCORE
        match_score = round(
            (temp_match * 0.3) + (budget_match * 0.3) + (timezone_score * 0.4),
            2
        )

        scored.append(CityScore(
            city=city,
            match_score=match_score,
            temp_match=round(temp_match, 2),
            budget_match=round(budget_match, 2),
            timezone_overlap_hours=round(timezone_overlap, 2)
        ))

    scored.sort(key=lambda x: x.match_score, reverse=True)

    return RecommendationResponse(user_id=user_id, recommendations=scored)

# GET a single city by id
@router.get("/{city_id}", response_model=CityResponse)
async def get_city(city_id: int, db: Session = Depends(get_db)):
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    return city

# UPDATE a city
@router.put("/{city_id}", response_model=CityResponse)
async def update_city(city_id: int, updated: CityCreate, db: Session = Depends(get_db)):
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    for key, value in updated.model_dump().items():
        setattr(city, key, value)
    db.commit()
    db.refresh(city)
    return city

# DELETE a city
@router.delete("/{city_id}")
async def delete_city(city_id: int, db: Session = Depends(get_db)):
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    db.delete(city)
    db.commit()
    return {"message": f"City {city.name} deleted successfully"}