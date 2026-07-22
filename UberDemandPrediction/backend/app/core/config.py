"""
Application configuration.
Loads settings from environment variables / .env file.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Uber Demand Prediction Platform"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # --- Mongo ---
    MONGO_URI: str = os.getenv(
        "MONGO_URI",
        "mongodb://localhost:27017",
    )
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "uber_demand_db")

    # --- JWT ---
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "CHANGE_THIS_SECRET_IN_PRODUCTION_9f8a7b6c5d4e3f2a1b0c",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- Model ---
    MODEL_PATH: str = os.getenv(
        "MODEL_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "trained_models",
            "uber_demand_model.joblib",
        ),
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
