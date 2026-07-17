from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/quakes"
    usgs_base: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    poll_seconds: int = 60
    min_magnitude: float = 3.0
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

settings = Settings()
