from fastapi import FastAPI
from app.config import settings
from app.database import engine, Base
import app.models
from app.routes import router as wallet_router

# Auto-create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Production-ready Wallet & Ledger Service with PostgreSQL",
)

# Register routes
app.include_router(wallet_router)
