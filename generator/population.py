from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
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
class TrafficSource:
    medium: str
    source: str
    campaign: str | None = None


@dataclass
class User:
    client_id: str
    user_id: str | None
    device: DeviceProfile
    geo: GeoProfile
    language: str
    is_returning: bool
    total_sessions: int
    acquisition_source: TrafficSource | None = None


def _make_client_id(rng: random.Random) -> str:
    return f"{rng.randint(10**9,10**10-1)}.{rng.randint(10**9,10**10-1)}"


def _weighted_choice(choices: List[Dict[str, Any]], rng: random.Random) -> Dict[str, Any]:
    weights = [c.get("weight", 1.0) for c in choices]
    return rng.choices(choices, weights=weights, k=1)[0]


def generate_users(n: int, config: Dict[str, Any] | None = None, seed: int = 42) -> List[User]:
    rng = random.Random(seed)
    users: List[User] = []

    device_mix = config.get("device_mix", []) if config else []
    geo_mix = config.get("geo_mix", []) if config else []
    traffic_sources = config.get("traffic_sources", []) if config else []

    for i in range(n):
        client_id = _make_client_id(rng)
        user_id = (f"user_{rng.randint(10000,99999)}" if rng.random() > 0.4 else None)

        # Sample device profile
        if device_mix:
            d = _weighted_choice(device_mix, rng)
            device = DeviceProfile(category=d.get("category", "mobile"), os=d.get("os", "Android"), browser=d.get("browser", "Chrome"))
        else:
            device = DeviceProfile(category="mobile", os="Android", browser="Chrome")

        # Sample geo profile
        if geo_mix:
            g = _weighted_choice(geo_mix, rng)
            # pick a region/city if available
            regions = g.get("regions") or []
            region = rng.choice(regions) if regions else None
            geo = GeoProfile(country=g.get("country", "Germany"), country_code=g.get("country_code", "DE"), region=region, city=region)
            language = "de-de" if geo.country_code in ("DE", "AT", "CH") else "en-us"
        else:
            geo = GeoProfile(country="Germany", country_code="DE", region="Berlin", city="Berlin")
            language = "de-de"

        # Sample acquisition source (first-session)
        acquisition = None
        if traffic_sources:
            ts = _weighted_choice(traffic_sources, rng)
            acquisition = TrafficSource(medium=ts.get("medium"), source=ts.get("source"), campaign=ts.get("campaign"))

        is_returning = rng.random() > (config.get("simulation", {}).get("new_to_returning_ratio", 0.75) if config else 0.75)
        total_sessions = 1 if not is_returning else rng.randint(2, 6)

        users.append(User(client_id=client_id, user_id=user_id, device=device, geo=geo, language=language, is_returning=is_returning, total_sessions=total_sessions, acquisition_source=acquisition))

    return users


__all__ = ["DeviceProfile", "GeoProfile", "TrafficSource", "User", "generate_users"]
