from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://127.0.0.1:5432/quakes"
    sql_echo: bool = False
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    usgs_base: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    poll_seconds: int = 60
    min_magnitude: float = 3.0
    semantic_scholar_api_key: str = ""
    openalex_email: str = ""
    rag_top_k: int = 6
    rag_vector_dimensions: int = 256
    rag_vector_store_path: str = "Project-Code/backend/.data/vector_index.json"
    rag_vector_store_dir: str = "Project-Code/backend/.data/vector_indexes"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_embedding_model: str = "text-embedding-3-small"

settings = Settings()
