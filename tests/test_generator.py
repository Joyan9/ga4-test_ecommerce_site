import unittest

from generator.products import build_catalog
from generator.population import generate_users
from generator.session import make_session_for_user
from generator.journey import build_simple_journey


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "simulation": {"currency": "EUR", "new_to_returning_ratio": 0.75, "daily": {"users_per_day_min": 1, "users_per_day_max": 5, "users_per_day_mean": 3, "users_per_day_std": 1}},
            "store": {"categories": [{"name": "Electronics", "price_range": [10.0, 100.0]}]},
            "funnel": {"page_view_to_view_item": 1.0, "view_item_to_add_to_cart": 1.0, "add_to_cart_to_begin_checkout": 1.0, "begin_checkout_to_purchase": 1.0},
        }

    def test_catalog_has_expected_count(self):
        catalog = build_catalog(self.config, seed=7, n=12)
        self.assertEqual(len(catalog), 12)
        self.assertTrue(all("item_id" in item and item["item_id"].startswith("PROD-") for item in catalog))

    def test_generate_users(self):
        users = generate_users(4, self.config, seed=10)
        self.assertEqual(len(users), 4)
        self.assertTrue(all("." in u.client_id for u in users))

    def test_journey_contains_page_view(self):
        catalog = build_catalog(self.config, seed=7, n=3)
        session = make_session_for_user(1, base_ts_s=1_700_000_000, seed=2)
        events = build_simple_journey(session, catalog, self.config, seed=11)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0].name, "page_view")


if __name__ == "__main__":
    unittest.main()
