from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PragatiDidi FastAPI"

    # ✅ ADD THIS LINE (missing earlier)
    base_url: str = "http://localhost:8000"

    # PostgreSQL
    pg_host: str
    pg_port: str = "5432"
    pg_user: str
    pg_password: str
    pg_database: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

