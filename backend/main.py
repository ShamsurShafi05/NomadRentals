from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import engine
from models import Base
from routers import cities, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates all tables on startup
    print("Tables created successfully")
    yield
    print("Server shutting down")

app = FastAPI(
    title="NomadRentals API",
    description="Smart city recommendations for remote workers",
    version="1.0.0"
)

app.include_router(cities.router)
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "NomadRentals API is running"}