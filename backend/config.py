"""
Configuration centralisée via Pydantic Settings.
Lit les variables d'environnement ou le fichier .env.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM : OpenAI ─────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Embeddings : sentence-transformers (local, multilingue) ──
    embed_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # ── ChromaDB (vector store local) ────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"

    # ── Base de données PostgreSQL ────────────────────────────
    database_url: str = "postgresql+asyncpg://hr_agent:hr_agent_pass@localhost:5432/hr_agent_db"

    # ── LangSmith (Observabilité LangGraph) ───────────────────
    langchain_tracing_v2: str = "false"
    langsmith_api_key: str = ""
    langsmith_project: str = "hr-agent-evaluateur"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # ── Fichiers uploadés ─────────────────────────────────────
    upload_dir: str = "./data/uploads"
    max_file_size_mb: int = 10

    # ── API ───────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    secret_key: str = "changeme_secret_key_min_32_chars_long"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
