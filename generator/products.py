from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import random

try:
    from faker import Faker
except ModuleNotFoundError:  # pragma: no cover - fallback for bare environments
    class Faker:  # type: ignore[no-redef]
        def seed_instance(self, seed: int) -> None:
            random.seed(seed)

        def catch_phrase(self) -> str:
            return "Smart Digital Solution"

        def company(self) -> str:
            return "Acme Corp"

        def word(self) -> str:
            return "premium"

        def color_name(self) -> str:
            return "Blue"


fake = Faker()


@dataclass
class Product:
    item_id: str
    item_name: str
    item_brand: str
    item_category: str
    item_category2: str | None
    price: float
    item_variant: str | None = None
    item_list_name: str | None = None
    item_list_id: str | None = None


def build_catalog(config: Dict[str, Any] | None = None, seed: int = 42, n: int = 80) -> List[Dict[str, Any]]:
    """Build a seeded product catalogue. Returns list of product dicts.

    Args:
        config: parsed config.yaml (optional). If provided, uses store.categories ranges.
        seed: RNG seed for reproducibility.
        n: number of products to generate.
    """
    random.seed(seed)
    fake.seed_instance(seed)

    categories = [
        {"name": "Electronics", "price_range": [29.99, 499.99]},
        {"name": "Clothing", "price_range": [9.99, 149.99]},
        {"name": "Home & Living", "price_range": [14.99, 299.99]},
        {"name": "Books", "price_range": [7.99, 39.99]},
    ]

    if config:
        store = config.get("store", {})
        if store.get("categories"):
            categories = store["categories"]

    products: List[Dict[str, Any]] = []
    for i in range(1, n + 1):
        cat = random.choices(categories, k=1)[0]
        price_min, price_max = cat.get("price_range", [10.0, 100.0])
        price = round(random.uniform(price_min, price_max), 2)
        item = Product(
            item_id=f"PROD-{i:04d}",
            item_name=fake.catch_phrase(),
            item_brand=fake.company().split()[0],
            item_category=cat.get("name", "Misc"),
            item_category2=(fake.word().title() if random.random() > 0.6 else None),
            price=price,
            item_variant=(None if random.random() > 0.7 else fake.color_name()),
            item_list_name=f"{cat.get('name', 'Catalog')} - Bestsellers",
            item_list_id=f"cat_{cat.get('name','misc').lower().replace(' ','_')}",
        )
        products.append(asdict(item))

    return products


__all__ = ["Product", "build_catalog"]
