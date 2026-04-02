import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PragatiDidi FastAPI"

    # AWS
    aws_region: str = os.getenv("AWS_REGION", "ap-south-1")

    # S3
    bucket_name: str = os.getenv("BUCKET_NAME", "pragatididi-2025")

    # PostgreSQL
    pg_host: str = os.getenv("POSTGRES_HOST")
    pg_port: str = os.getenv("POSTGRES_PORT", "5432")
    pg_user: str = os.getenv("POSTGRES_USER")
    pg_password: str = os.getenv("POSTGRES_PASSWORD")
    pg_database: str = os.getenv("POSTGRES_DATABASE")

    class Config:
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()