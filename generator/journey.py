from typing import List, Dict, Any
import random
import time
from generator.session import Event, Session


def build_simple_journey(session: Session, products: List[Dict[str, Any]], config: Dict[str, Any] | None = None, seed: int = 0) -> List[Event]:
    rng = random.Random(seed + session.session_number)
    events: List[Event] = []
    ts = session.start_timestamp_us
    # page_view (homepage)
    params = {
        "session_id": session.session_id,
        "session_number": session.session_number,
        "engagement_time_msec": max(100, session.engagement_time_msec // 4),
        "language": "de-de",
        "page_location": "https://demoshop.example.com/",
        "page_title": "Homepage",
    }
    events.append(Event(name="page_view", timestamp_micros=ts, params=params))

    # maybe view item
    if rng.random() < (config.get("funnel", {}).get("page_view_to_view_item", 0.55) if config else 0.55):
        ts += rng.randint(5_000_000, 30_000_000)
        prod = rng.choice(products)
        params = {
            "session_id": session.session_id,
            "session_number": session.session_number,
            "engagement_time_msec": max(100, session.engagement_time_msec // 4),
            "language": "de-de",
            "page_location": f"https://demoshop.example.com/product/{prod['item_id']}",
            "page_title": prod["item_name"],
            "currency": config.get("simulation", {}).get("currency", "EUR") if config else "EUR",
            "value": prod.get("price", 0.0),
            "items": [{"item_id": prod["item_id"], "item_name": prod["item_name"], "price": prod.get("price", 0.0), "quantity": 1}],
        }
        events.append(Event(name="view_item", timestamp_micros=ts, params=params))

        # maybe add_to_cart
        if rng.random() < (config.get("funnel", {}).get("view_item_to_add_to_cart", 0.28) if config else 0.28):
            ts += rng.randint(3_000_000, 20_000_000)
            params2 = dict(params)
            params2["engagement_time_msec"] = max(50, session.engagement_time_msec // 6)
            params2["value"] = params.get("value", 0.0)
            events.append(Event(name="add_to_cart", timestamp_micros=ts, params=params2))

            # maybe begin_checkout -> purchase
            if rng.random() < (config.get("funnel", {}).get("add_to_cart_to_begin_checkout", 0.55) if config else 0.55):
                ts += rng.randint(5_000_000, 40_000_000)
                bc = {"session_id": session.session_id, "session_number": session.session_number, "engagement_time_msec": 200, "currency": config.get("simulation", {}).get("currency", "EUR") if config else "EUR", "value": params.get("value", 0.0), "items": params.get("items", [])}
                events.append(Event(name="begin_checkout", timestamp_micros=ts, params=bc))

                if rng.random() < (config.get("funnel", {}).get("begin_checkout_to_purchase", 0.60) if config else 0.60):
                    ts += rng.randint(5_000_000, 60_000_000)
                    txn = f"TXN-{int(time.time())}-{rng.randint(1000,9999)}"
                    purchase = {"transaction_id": txn, "value": params.get("value", 0.0), "currency": config.get("simulation", {}).get("currency", "EUR") if config else "EUR", "items": params.get("items", [])}
                    events.append(Event(name="purchase", timestamp_micros=ts, params=purchase))

    return events


__all__ = ["build_simple_journey"]
