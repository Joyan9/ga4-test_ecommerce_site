from typing import List, Dict, Any
import random
import time
from generator.session import Event, Session


def build_simple_journey(session: Session, products: List[Dict[str, Any]], config: Dict[str, Any] | None = None, seed: int = 0) -> List[Event]:
    rng = random.Random(seed + session.session_number)
    events: List[Event] = []
    ts = session.start_timestamp_us
    # session_start (session initialization)
    session_start_params = {
        "session_id": session.session_id,
        "session_number": session.session_number,
        "engagement_time_msec": max(100, session.engagement_time_msec // 4),
        "language": "de-de",
        "page_location": "https://demoshop.example.com/",
        "page_title": "Homepage",
    }
    events.append(Event(name="session_start", timestamp_micros=ts, params=session_start_params))
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
    # maybe browse list
    if rng.random() < (config.get("funnel", {}).get("page_view_to_view_item_list", 0.65) if config else 0.65):
        ts += rng.randint(2_000_000, 12_000_000)
        list_params = {
            "session_id": session.session_id,
            "session_number": session.session_number,
            "engagement_time_msec": max(100, session.engagement_time_msec // 5),
            "language": "de-de",
            "page_location": "https://demoshop.example.com/category/electronics",
            "page_title": "Category Listing",
        }
        # record a page_view for the listing page
        page_list_params = {"session_id": session.session_id, "session_number": session.session_number, "engagement_time_msec": list_params["engagement_time_msec"], "language": list_params["language"], "page_location": list_params["page_location"], "page_title": list_params["page_title"]}
        events.append(Event(name="page_view", timestamp_micros=ts, params=page_list_params))
        events.append(Event(name="view_item_list", timestamp_micros=ts, params=list_params))

        # maybe search
        if rng.random() < (config.get("funnel", {}).get("view_item_list_to_search", 0.15) if config else 0.15):
            ts += rng.randint(1_000_000, 8_000_000)
            events.append(Event(name="search", timestamp_micros=ts, params={"session_id": session.session_id, "query": "wireless headphones"}))

        # maybe view item
        if rng.random() < (config.get("funnel", {}).get("page_view_to_view_item", 0.55) if config else 0.55):
            ts += rng.randint(3_000_000, 30_000_000)
            prod = rng.choice(products)
            items = [{"item_id": prod["item_id"], "item_name": prod["item_name"], "price": prod.get("price", 0.0), "quantity": 1}]
            value = sum(it.get("price", 0.0) * it.get("quantity", 1) for it in items)
            params = {
                "session_id": session.session_id,
                "session_number": session.session_number,
                "engagement_time_msec": max(100, session.engagement_time_msec // 4),
                "language": "de-de",
                "page_location": f"https://demoshop.example.com/product/{prod['item_id']}",
                "page_title": prod["item_name"],
                "currency": config.get("simulation", {}).get("currency", "EUR") if config else "EUR",
                "value": value,
                "items": items,
            }
            # record a page_view for the product page
            page_prod_params = {"session_id": session.session_id, "session_number": session.session_number, "engagement_time_msec": params["engagement_time_msec"], "language": params["language"], "page_location": params["page_location"], "page_title": params["page_title"]}
            events.append(Event(name="page_view", timestamp_micros=ts, params=page_prod_params))
            events.append(Event(name="view_item", timestamp_micros=ts, params=params))

            # maybe select item (e.g., variant/select)
            if rng.random() < (config.get("funnel", {}).get("view_item_to_select", 0.25) if config else 0.25):
                ts += rng.randint(500_000, 5_000_000)
                events.append(Event(name="select_item", timestamp_micros=ts, params={"session_id": session.session_id, "items": items}))

            # maybe add_to_cart
            if rng.random() < (config.get("funnel", {}).get("view_item_to_add_to_cart", 0.28) if config else 0.28):
                ts += rng.randint(1_000_000, 20_000_000)
                params2 = dict(params)
                params2["engagement_time_msec"] = max(50, session.engagement_time_msec // 6)
                params2["value"] = sum(it.get("price", 0.0) * it.get("quantity", 1) for it in params2.get("items", []))
                events.append(Event(name="add_to_cart", timestamp_micros=ts, params=params2))

                # maybe view cart
                if rng.random() < (config.get("funnel", {}).get("add_to_cart_to_view_cart", 0.6) if config else 0.6):
                    ts += rng.randint(500_000, 8_000_000)
                    cart = {"session_id": session.session_id, "items": params2.get("items", []), "value": params2.get("value", 0.0)}
                    # record a page_view for the cart page
                    page_cart_params = {"session_id": session.session_id, "session_number": session.session_number, "engagement_time_msec": max(50, session.engagement_time_msec // 6), "language": "de-de", "page_location": "https://demoshop.example.com/cart", "page_title": "Cart"}
                    events.append(Event(name="page_view", timestamp_micros=ts, params=page_cart_params))
                    events.append(Event(name="view_cart", timestamp_micros=ts, params=cart))

                # maybe begin_checkout -> add shipping/payment -> purchase
                if rng.random() < (config.get("funnel", {}).get("add_to_cart_to_begin_checkout", 0.55) if config else 0.55):
                    ts += rng.randint(5_000_000, 40_000_000)
                    bc = {"session_id": session.session_id, "session_number": session.session_number, "engagement_time_msec": 200, "currency": config.get("simulation", {}).get("currency", "EUR") if config else "EUR", "value": params2.get("value", 0.0), "items": params2.get("items", [])}
                    events.append(Event(name="begin_checkout", timestamp_micros=ts, params=bc))

                    if rng.random() < (config.get("funnel", {}).get("begin_checkout_to_add_shipping", 0.8) if config else 0.8):
                        ts += rng.randint(1_000_000, 10_000_000)
                        events.append(Event(name="add_shipping_info", timestamp_micros=ts, params={"session_id": session.session_id, "shipping_tier": "standard"}))

                    if rng.random() < (config.get("funnel", {}).get("add_shipping_to_add_payment", 0.9) if config else 0.9):
                        ts += rng.randint(1_000_000, 10_000_000)
                        events.append(Event(name="add_payment_info", timestamp_micros=ts, params={"session_id": session.session_id, "payment_method": "card"}))

                    if rng.random() < (config.get("funnel", {}).get("begin_checkout_to_purchase", 0.60) if config else 0.60):
                        ts += rng.randint(5_000_000, 60_000_000)
                        txn = f"TXN-{int(time.time())}-{rng.randint(1000,9999)}"
                        purchase = {"transaction_id": txn, "value": params2.get("value", 0.0), "currency": config.get("simulation", {}).get("currency", "EUR") if config else "EUR", "items": params2.get("items", [])}
                        events.append(Event(name="purchase", timestamp_micros=ts, params=purchase))

    return events


__all__ = ["build_simple_journey"]
