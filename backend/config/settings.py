from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


class AppSettings(BaseSettings):
    """
    Application settings, loaded from environment variables.
    Utilizes pydantic for validation.
    """
    # --- Application Metadata ---
    APP_TITLE: str = "Data Preprocessing Constructor API"
    APP_DESCRIPTION: str = "An API for analyzing and preprocessing datasets."
    APP_VERSION: str = "1.0.0"

    # --- Server Configuration ---
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    RELOAD: bool = True  # Set to False in production

    # --- CORS Settings ---
    ALLOWED_ORIGINS: List[str] = ["*"]  # Should be restricted in production

    # --- Directory Paths ---
    # Base directory for the application's data
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data/uploads"
    PROCESSED_DIR: Path = BASE_DIR / "data/processed"
    TEMP_DIR: Path = BASE_DIR / "data/temp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Instantiate the settings object for easy import across the application
settings = AppSettings()