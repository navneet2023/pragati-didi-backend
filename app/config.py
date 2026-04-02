from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PragatiDidi FastAPI"
    aws_region: str = "ap-south-1"
    learner_table: str = "learner_details"
    bucket_name: str = "pragatididi-2025"

    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = "pgadmin"
    pg_database: str = "postgres"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()