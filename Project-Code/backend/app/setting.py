from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://127.0.0.1:5432/quakes"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    usgs_base: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    poll_seconds: int = 60
    min_magnitude: float = 3.0
    semantic_scholar_api_key: str = ""
    openalex_email: str = ""

settings = Settings()
