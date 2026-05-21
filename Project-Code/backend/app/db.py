from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from .setting import settings

DATABASE_URL = settings.database_url
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not configured. Check Project-Code/backend/.env")

engine = create_engine(DATABASE_URL, echo=settings.sql_echo, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
