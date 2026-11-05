import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Base Directory of Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env if present
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    # App Information
    PROJECT_NAME: str = "Business Insights Copilot"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # OpenAI & LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ROUTER_MODEL: str = os.getenv("ROUTER_MODEL", "gpt-4o-mini")
    SQL_MODEL: str = os.getenv("SQL_MODEL", "gpt-4o-mini")
    RAG_MODEL: str = os.getenv("RAG_MODEL", "gpt-4o-mini")
    SYNTHESIS_MODEL: str = os.getenv("SYNTHESIS_MODEL", "gpt-4o")

    # Embeddings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")  # or 'openai'
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 4

    # MySQL Database Config (Standard Connection)
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "business_copilot")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "copilot_user")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "copilot_pass")

    # MySQL Read-Only User (for SQL Agent execution safety)
    MYSQL_READONLY_USER: str = os.getenv("MYSQL_READONLY_USER", "copilot_readonly")
    MYSQL_READONLY_PASSWORD: str = os.getenv("MYSQL_READONLY_PASSWORD", "readonly_pass")

    # Paths
    DOCUMENTS_DIR: Path = BASE_DIR / "data" / "documents"
    FAISS_INDEX_DIR: Path = BASE_DIR / "data" / "faiss_index"

    # Server Ports
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", 8000))
    BACKEND_API_URL: str = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", 8501))

    @property
    def mysql_admin_uri(self) -> str:
        """SQLAlchemy connection string for admin/setup migrations."""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def mysql_readonly_uri(self) -> str:
        """SQLAlchemy connection string strictly constrained to SELECT privileges."""
        return f"mysql+pymysql://{self.MYSQL_READONLY_USER}:{self.MYSQL_READONLY_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

