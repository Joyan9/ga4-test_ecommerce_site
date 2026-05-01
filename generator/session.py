from dataclasses import dataclass
from typing import List
import time
import random


@dataclass
class Event:
    name: str
    timestamp_micros: int
    params: dict


@dataclass
class Session:
    session_id: int
    session_number: int
    start_timestamp_us: int
    engagement_time_msec: int
    events: List[Event]


def make_session_for_user(session_number: int, base_ts_s: int | None = None, seed: int = 0) -> Session:
    rng = random.Random(seed + session_number)
    start = int((base_ts_s or int(time.time())) * 1_000_000)
    engagement = rng.randint(500, 5_000)
    return Session(session_id=int(start // 1_000_000), session_number=session_number, start_timestamp_us=start, engagement_time_msec=engagement, events=[])


__all__ = ["Event", "Session", "make_session_for_user"]
