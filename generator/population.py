from dataclasses import dataclass
from typing import Dict, Any, List
import random


@dataclass
class DeviceProfile:
    category: str
    os: str
    browser: str


@dataclass
class GeoProfile:
    country: str
    country_code: str
    region: str | None = None
    city: str | None = None


@dataclass
class User:
    client_id: str
    user_id: str | None
    device: DeviceProfile
    geo: GeoProfile
    language: str
    is_returning: bool
    total_sessions: int


def _make_client_id(rng: random.Random) -> str:
    return f"{rng.randint(10**9,10**10-1)}.{rng.randint(10**9,10**10-1)}"


def generate_users(n: int, config: Dict[str, Any] | None = None, seed: int = 42) -> List[User]:
    rng = random.Random(seed)
    users: List[User] = []
    for i in range(n):
        client_id = _make_client_id(rng)
        user_id = (f"user_{rng.randint(10000,99999)}" if rng.random() > 0.4 else None)
        # simple device/geo picks if config not provided
        device = DeviceProfile(category="mobile", os="Android", browser="Chrome")
        geo = GeoProfile(country="Germany", country_code="DE", region="Berlin", city="Berlin")
        language = "de-de"
        is_returning = rng.random() > (config.get("simulation", {}).get("new_to_returning_ratio", 0.75) if config else 0.75)
        total_sessions = 1 if not is_returning else rng.randint(2, 5)
        users.append(User(client_id=client_id, user_id=user_id, device=device, geo=geo, language=language, is_returning=is_returning, total_sessions=total_sessions))

    return users


__all__ = ["DeviceProfile", "GeoProfile", "User", "generate_users"]
