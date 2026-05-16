from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / ".data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(BACKEND_DIR / ".env.local")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://127.0.0.1:5432/quakes"
    sql_echo: bool = False
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8001
    usgs_base: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    poll_seconds: int = 60
    min_magnitude: float = 3.0
    semantic_scholar_api_key: str = ""
    openalex_email: str = ""
    raganything_enabled: bool = True
    raganything_source_dir: str = str(BACKEND_DIR.parents[1] / "RAG-Anything-main")
    raganything_working_dir: str = str(DATA_DIR / "raganything")
    raganything_output_dir: str = str(DATA_DIR / "raganything_output")
    raganything_document_dir: str = str(DATA_DIR / "documents")
    raganything_parser: str = "mineru"
    raganything_parse_method: str = "auto"
    raganything_allow_parse_fallback: bool = True
    raganything_parse_fallback_method: str = "local-text"
    raganything_query_mode: str = "hybrid"
    raganything_allow_query_fallback: bool = True
    raganything_query_fallback_mode: str = "naive"
    raganything_llm_model: str = "gpt-4o-mini"
    raganything_vision_model: str = "gpt-4o"
    raganything_embedding_dim: int = 1536
    raganything_max_token_size: int = 8192
    raganything_max_concurrent_files: int = 1
    raganything_enable_image_processing: bool = True
    raganything_enable_table_processing: bool = True
    raganything_enable_equation_processing: bool = True
    paper_database_path: str = str(DATA_DIR / "papers.sqlite")
    geo_rag_engine: str = "raganything"
    geo_rag_chat_model: str = "gpt-4o-mini"
    geo_rag_index_version: str = "geo-rag-v1"
    geo_rag_embedding_provider: str = "auto"
    geo_rag_embedding_url: str = ""
    geo_rag_embedding_api_key: str = ""
    geo_rag_embedding_allow_fallback: bool = True
    geo_rag_embedding_model: str = ""
    geo_rag_embedding_dim: int = 1536
    geo_rag_embedding_batch_size: int = 32
    geo_rag_storage_backend: str = "local"
    geo_rag_storage_root: str = str(DATA_DIR / "geo_rag_documents")
    geo_rag_upload_stage_root: str = str(DATA_DIR / "geo_rag_upload_stage")
    geo_rag_storage_remote_root: str = "/opt/cudtseis_web/storage/geo_rag_documents"
    geo_rag_storage_public_base_url: str = ""
    geo_rag_storage_ssh_host: str = ""
    geo_rag_storage_ssh_user: str = "root"
    geo_rag_storage_ssh_port: int = 22
    geo_rag_storage_ssh_key_path: str = ""
    geo_rag_import_worker_enabled: bool = True
    geo_rag_import_workers: int = 1
    geo_rag_import_worker_poll_seconds: float = 2.0
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_embedding_model: str = "text-embedding-3-small"


settings = Settings()
