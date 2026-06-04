from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import engine
from models import Base
from routers import cities, users, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates all tables on startup
    print("Tables created successfully")
    yield
    print("Server shutting down")

app = FastAPI(
    title="NomadRentals API",
    description="Smart city recommendations for remote workers",
    version="1.0.0",
    lifespan=lifespan                      # V Imp: this is what runs the code to create tables on startup
)

app.include_router(cities.router)
app.include_router(users.router)
# auth
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "NomadRentals API is running"}