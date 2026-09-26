from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.routes.nonprofits import router as nonprofits_router
from app.routes.vendors import router as vendors_router


app = FastAPI(
    title="Nonprofit Vendor Payment and Transparency Platform",
    version="0.1.0",
)

app.include_router(nonprofits_router)
app.include_router(vendors_router)


@app.get("/")
def root():
    return {
        "message": "Nonprofit Vendor Payment Platform API is running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/database")
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }