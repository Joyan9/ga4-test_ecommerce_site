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
    # Harden ecommerce values: if an event contains `items`, compute a `value` from item prices*quantity
    def _compute_items_value(items: List[Dict[str, Any]]) -> float:
        total = 0.0
        for it in items:
            try:
                price = float(it.get("price", 0.0))
            except Exception:
                price = 0.0
            try:
                qty = int(it.get("quantity", 1))
            except Exception:
                qty = 1
            total += price * qty
        return round(total, 2)

    for ev in body.get("events", []):
        params = ev.get("params") or {}
        items = params.get("items")
        if isinstance(items, list) and items:
            # normalize item fields and ensure quantities
            for it in items:
                if "quantity" not in it:
                    it["quantity"] = 1
                if "price" in it:
                    try:
                        it["price"] = float(it["price"])
                    except Exception:
                        it["price"] = 0.0
            computed = _compute_items_value(items)
            # Set `value` if missing or zero
            if not params.get("value") or float(params.get("value", 0.0)) == 0.0:
                params["value"] = computed
            ev["params"] = params

    return body


def make_page_view_event(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"name": "page_view", "params": params}


__all__ = ["build_event_payload", "make_page_view_event"]
