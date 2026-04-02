from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PragatiDidi FastAPI"
    aws_region: str = "ap-south-1"
    learner_table: str = "learner_details"
    bucket_name: str = "pragatididi-2025"

    # ✅ Let pydantic read env variables automatically
    pg_host: str
    pg_port: int = 5432
    pg_user: str
    pg_password: str
    pg_database: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()