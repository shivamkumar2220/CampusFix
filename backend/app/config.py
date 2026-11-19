"""Reads all settings from the .env file so no secrets are hard-coded in the code."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load the variables from backend/.env into the environment (if the file exists)
load_dotenv()


def read_bool_setting(name: str, default: bool) -> bool:
    """Read a true/false setting such as ENABLE_SCHEDULER=true from the environment."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    """All configuration values used by the application."""

    # Database connection
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "campusfix")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")

    # JWT login tokens
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-this-secret-key")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Background SLA job
    enable_scheduler: bool = read_bool_setting("ENABLE_SCHEDULER", True)
    sla_check_interval_minutes: int = int(os.getenv("SLA_CHECK_INTERVAL_MINUTES", "15"))

    # CORS: comma separated list of allowed frontend origins, or * for all
    cors_allowed_origins: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    def get_cors_origins_list(self) -> list[str]:
        """Turn the comma separated CORS_ALLOWED_ORIGINS value into a list."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
