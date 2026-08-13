from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg2://pathfinder:pathfinder@localhost:5433/pathfinder"
    )
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
