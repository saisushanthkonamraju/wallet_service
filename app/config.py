import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")


class Settings:
    DATABASE_URL: str = os.environ["DATABASE_URL"]  # Fails hard if not set in .env
    APP_TITLE: str = "Wallet & Ledger Service"
    APP_VERSION: str = "1.0.0"


settings = Settings()
