from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

from uvicorn import Config

from backend.models import City

# Your SQLAlchemy model has ALL columns including sensitive ones like email, and also relationships to other tables.
# Your Pydantic schema controls what the API actually returns
# SQLAlchemy is your database layer, Pydantic is your API layer. 
# They intentionally know nothing about each other. 
# The route function in the middle is what translates between them


# Base = shared fields
# Create = what client sends in 
# Response = what you send back (always has id + Config).'


# ─── CITY ───────────────────────────────────────────

class CityBase(BaseModel):
    name: str
    country: str
    timezone: Optional[str] = None
    avg_temp: Optional[float] = None
    monthly_cost: Optional[int] = None
    wifi_speed: Optional[int] = None
    safety_score: Optional[int] = None
    nomad_score: Optional[int] = None

# Just a base class for the city model.

class CityCreate(CityBase):
    pass

# This is what the client sends when creating a city. 
# Right now it's identical to CityBase so it just says pass. 
# But later if you want to add fields only needed at creation time (like a secret key), you add them here 
# [ without touching CityBase. It's future-proofing. ]

class CityResponse(CityBase):
    id: int

    class Config:                       # V Imp
        from_attributes = True

# This is what you send back to the client after creating/fetching a city.

#  id: int — the client didn't send an id (the database generated it), 
#  but the response includes it so the client knows which city was created.

# class Config: from_attributes = True — this is the important one. 
# It tells Pydantic to read the data from the SQLAlchemy model's attributes,
# Pydantic would crash because it expects a dictionary, not a SQLAlchemy object.
# from_attributes = True tells Pydantic "also accept objects, read their attributes directly." 
# So city.name, city.id etc. get read automatically.
# And this works fine:    city = db.query(City).first()  # this is a SQLAlchemy object
#                         return city                     # Pydantic tries to read it

# Only Response schemas need Config — because only responses return SQLAlchemy objects. 
# Create schemas receive plain JSON dictionaries from the client, so they never need it.

# ─── USER ───────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── USER PREFERENCE ────────────────────────────────

class UserPreferenceBase(BaseModel):
    preferred_temp: Optional[int] = None
    max_budget: Optional[int] = None
    client_timezone: Optional[str] = None
    work_start_hour: Optional[int] = None
    work_end_hour: Optional[int] = None
    climate_type: Optional[str] = None

class UserPreferenceCreate(UserPreferenceBase):
    pass

class UserPreferenceResponse(UserPreferenceBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ─── TRACKED CITY ───────────────────────────────────

class TrackedCityCreate(BaseModel):
    city_id: int
    alert_enabled: bool = False

class TrackedCityResponse(BaseModel):
    id: int
    user_id: int
    city_id: int
    added_at: datetime
    alert_enabled: bool
    city: CityResponse

    class Config:
        from_attributes = True