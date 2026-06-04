from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

# Your SQLAlchemy model has ALL columns including sensitive ones like email, and also relationships to other tables.
# Your Pydantic schema controls what the API actually returns
# SQLAlchemy is your database layer, Pydantic is your API layer. 
# They intentionally know nothing about each other. 
# The route function in the middle is what translates between them

class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    timezone = Column(String(50))
    avg_temp = Column(Float)
    monthly_cost = Column(Integer)
    wifi_speed = Column(Integer)
    safety_score = Column(Integer)
    nomad_score = Column(Integer)

    tracked_by = relationship("TrackedCity", back_populates="city")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    # for auth
    hashed_password = Column(String(255), nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    tracked_cities = relationship("TrackedCity", back_populates="user")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    preferred_temp = Column(Integer)
    max_budget = Column(Integer)
    client_timezone = Column(String(50))
    work_start_hour = Column(Integer)
    work_end_hour = Column(Integer)
    climate_type = Column(String(50))

    user = relationship("User", back_populates="preferences")


class TrackedCity(Base):
    __tablename__ = "tracked_cities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    alert_enabled = Column(Boolean, default=False)

    user = relationship("User", back_populates="tracked_cities")
    city = relationship("City", back_populates="tracked_by")