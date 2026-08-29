from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    """Render/Heroku often supply postgres:// — normalize for SQLAlchemy + psycopg2."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", "../.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = Field(
        default="postgresql+psycopg2://pathfinder:pathfinder@localhost/pathfinder",
        description="PostgreSQL URL. Set DATABASE_URL in .env.local (see .env.example).",
    )
    api_host: str = "0.0.0.0"
    api_port: int | None = Field(default=None, alias="API_PORT")
    cors_origins: str = Field(
        default="",
        alias="PATHFINDER_CORS_ORIGINS",
        description="Comma-separated browser origins allowed by CORS (e.g. http://localhost:3000).",
    )
    ai_provider: str = Field(default="stub", alias="PATHFINDER_AI_PROVIDER")
    ai_model: str = Field(default="gpt-4o-mini", alias="PATHFINDER_AI_MODEL")
    ai_api_key: str = Field(default="", alias="PATHFINDER_AI_API_KEY")
    ai_base_url: str = Field(default="https://api.openai.com/v1", alias="PATHFINDER_AI_BASE_URL")
    ai_timeout_seconds: float = Field(default=8.0, alias="PATHFINDER_AI_TIMEOUT_SECONDS")
    semantic_enabled: bool = Field(default=True, alias="PATHFINDER_SEMANTIC_ENABLED")
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="PATHFINDER_EMBEDDING_MODEL")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_database_url(value)
        return value


settings = Settings()
