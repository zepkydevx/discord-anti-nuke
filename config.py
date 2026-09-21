"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when a required configuration value is missing."""


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings."""

    token: str
    log_level: str = "INFO"
    database_path: str = "antinuke.db"


def load_settings() -> Settings:
    """Build ``Settings`` from the environment.

    A local ``.env`` file is loaded first if it exists, so the token never
    has to be written in the source code or committed to the repository.
    """
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in."
        )

    return Settings(
        token=token,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        database_path=os.getenv("DATABASE_PATH", "antinuke.db"),
    )
