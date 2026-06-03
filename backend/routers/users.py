from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, UserPreference, TrackedCity
from schemas import (
    UserCreate, UserResponse,
    UserPreferenceCreate, UserPreferenceResponse,
    TrackedCityCreate, TrackedCityResponse
)

router = APIRouter(prefix="/users", tags=["users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE a user
@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# GET a user by id
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# SAVE user preferences
@router.post("/{user_id}/preferences", response_model=UserPreferenceResponse)
async def save_preferences(user_id: int, prefs: UserPreferenceCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if existing:
        for key, value in prefs.model_dump().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    new_prefs = UserPreference(user_id=user_id, **prefs.model_dump())
    db.add(new_prefs)
    db.commit()
    db.refresh(new_prefs)
    return new_prefs

# GET user preferences
@router.get("/{user_id}/preferences", response_model=UserPreferenceResponse)
async def get_preferences(user_id: int, db: Session = Depends(get_db)):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="No preferences found for this user")
    return prefs

# TRACK a city
@router.post("/{user_id}/track", response_model=TrackedCityResponse)
async def track_city(user_id: int, body: TrackedCityCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    city = db.query(TrackedCity).filter(
        TrackedCity.user_id == user_id,
        TrackedCity.city_id == body.city_id
    ).first()
    if city:
        raise HTTPException(status_code=400, detail="City already tracked")
    tracked = TrackedCity(user_id=user_id, **body.model_dump())
    db.add(tracked)
    db.commit()
    db.refresh(tracked)
    return tracked

# GET all tracked cities for a user
@router.get("/{user_id}/tracked", response_model=list[TrackedCityResponse])
async def get_tracked_cities(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tracked = db.query(TrackedCity).filter(TrackedCity.user_id == user_id).all()
    return tracked