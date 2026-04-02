from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "PragatiDidi FastAPI"
    aws_region: str = "ap-south-1"
    learner_table: str = "learner_details"
    bucket_name: str = "pragatididi-2025"

    # ✅ Map Railway env variables correctly
    pg_host: str = Field(alias="POSTGRES_HOST")
    pg_port: int = Field(default=5432, alias="POSTGRES_PORT")
    pg_user: str = Field(alias="POSTGRES_USER")
    pg_password: str = Field(alias="POSTGRES_PASSWORD")
    pg_database: str = Field(alias="POSTGRES_DATABASE")  # 👈 IMPORTANT FIX

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()