from typing import Dict, Any, List
import time


def _now_micros() -> int:
    return int(time.time() * 1_000_000)


def build_event_payload(
    client_id: str,
    events: List[Dict[str, Any]],
    user_id: str | None = None,
    timestamp_micros: int | None = None,
    user_properties: Dict[str, Dict[str, Any]] | None = None,
    geo: Dict[str, str] | None = None,
    device: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    """Build a minimal MP request body.

    `events` should be a list of dicts with `name` and `params` keys.
    """
    body: Dict[str, Any] = {"client_id": client_id}
    if user_id:
        body["user_id"] = user_id
    body["timestamp_micros"] = timestamp_micros or _now_micros()
    if user_properties:
        body["user_properties"] = user_properties
    if geo:
        body["geo"] = geo
    if device:
        body["device"] = device

    body["events"] = events
    return body


def make_page_view_event(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"name": "page_view", "params": params}


__all__ = ["build_event_payload", "make_page_view_event"]
