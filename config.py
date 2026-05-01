from dataclasses import dataclass
from typing import Any, Dict
import os
import yaml
from dotenv import load_dotenv


load_dotenv()


@dataclass
class EnvConfig:
    measurement_id: str
    api_secret: str


@dataclass
class Config:
    env: EnvConfig
    raw: Dict[str, Any]


def load_config(path: str = "config.yaml") -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    measurement_id = os.getenv("GA4_MEASUREMENT_ID")
    api_secret = os.getenv("GA4_API_SECRET")
    if not measurement_id or not api_secret:
        raise EnvironmentError("GA4_MEASUREMENT_ID and GA4_API_SECRET must be set in environment (.env)")

    envc = EnvConfig(measurement_id=measurement_id, api_secret=api_secret)
    return Config(env=envc, raw=raw or {})


__all__ = ["load_config", "Config", "EnvConfig"]
