from fastapi import FastAPI
from app.database import engine, Base
import app.models
from app.routes import router as wallet_router

# Auto-create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Register routes
app.include_router(wallet_router)
