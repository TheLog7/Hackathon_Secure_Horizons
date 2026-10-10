"""Central configuration, read from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    USE_REAL_BEDROCK: bool = _bool("USE_REAL_BEDROCK", False)
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-5-5-20251101-v1:0"
    )

    ENGINE_URL: str = os.getenv("ENGINE_URL", "http://localhost:8000")

    DB_PATH: str = os.getenv("DB_PATH", str(ROOT / "secure_horizons.db"))

    # Where the generated synthetic company lives
    DATA_DIR: Path = ROOT / "data"


config = Config()
