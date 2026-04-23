import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from .setting import settings

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL") or settings.database_url
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not configured. Check Project-Code/backend/.env")

engine = create_engine(DATABASE_URL, echo=settings.sql_echo)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
