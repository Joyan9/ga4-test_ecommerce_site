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
    """Create a Session with a start timestamp sampled from an intraday distribution.

    - `base_ts_s` should be a seconds-since-epoch representing the day's midnight (or a reference second).
    - session_id is derived as `int(session_start_seconds)` per GA4 convention.
    """
    rng = random.Random(seed + session_number)

    # reference day start (seconds). If not provided, use today's midnight as base.
    if base_ts_s is None:
        # use current time's date midnight
        now = time.localtime()
        base_day = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0, 0, 0, -1))
        base_ts_s = int(base_day)

    # intraday hour weights: peaks 09-11 and 19-22, trough 02-06
    hour_weights = [1.0] * 24
    for h in (9, 10, 11, 19, 20, 21, 22):
        hour_weights[h] = 4.0
    for h in (2, 3, 4, 5, 6):
        hour_weights[h] = 0.3

    hour = rng.choices(list(range(24)), weights=hour_weights, k=1)[0]
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    micro = rng.randint(0, 999_999)

    start_s = int(base_ts_s) + hour * 3600 + minute * 60 + second
    start_us = int(start_s * 1_000_000 + micro)

    engagement = rng.randint(500, 5_000)
    session_id = int(start_s)

    return Session(session_id=session_id, session_number=session_number, start_timestamp_us=start_us, engagement_time_msec=engagement, events=[])


__all__ = ["Event", "Session", "make_session_for_user"]
