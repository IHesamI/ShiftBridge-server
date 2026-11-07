from fastapi import FastAPI
from database import engine, Base
import models
from routes import auth

# Create SQLite tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShiftBridge API", version="1.0.0")

app.include_router(auth.router)

@app.get("/")
def root():
    return {"status": "healthy", "service": "ShiftBridge API"}