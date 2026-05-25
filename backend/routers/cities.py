from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import City
from schemas import CityCreate, CityResponse

router = APIRouter(prefix="/cities", tags=["cities"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE a city
@router.post("/", response_model=CityResponse)
async def create_city(city: CityCreate, db: Session = Depends(get_db)):
    new_city = City(**city.model_dump())
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