from typing import TypedDict, List, Dict, Any


class ItemDict(TypedDict, total=False):
    item_id: str
    item_name: str
    item_brand: str
    item_category: str
    item_category2: str
    item_variant: str
    price: float
    quantity: int
    index: int
    item_list_id: str
    item_list_name: str


class EventParamDict(TypedDict, total=False):
    session_id: int
    session_number: int
    engagement_time_msec: int
    language: str
    screen_resolution: str
    page_location: str
    page_title: str
    currency: str
    value: float
    items: List[ItemDict]
    transaction_id: str


class MPEventDict(TypedDict):
    name: str
    params: EventParamDict


class MPRequestDict(TypedDict, total=False):
    client_id: str
    user_id: str
    timestamp_micros: int
    user_properties: Dict[str, Dict[str, Any]]
    events: List[MPEventDict]


__all__ = ["ItemDict", "EventParamDict", "MPEventDict", "MPRequestDict"]
