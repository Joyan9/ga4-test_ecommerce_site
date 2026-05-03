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

    def test_journey_starts_with_session_start(self):
        catalog = build_catalog(self.config, seed=7, n=3)
        session = make_session_for_user(1, base_ts_s=1_700_000_000, seed=2)
        events = build_simple_journey(session, catalog, self.config, seed=11)
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[0].name, "session_start")
        self.assertEqual(events[1].name, "page_view")

    def test_session_start_has_correct_params(self):
        catalog = build_catalog(self.config, seed=7, n=3)
        session = make_session_for_user(1, base_ts_s=1_700_000_000, seed=2)
        events = build_simple_journey(session, catalog, self.config, seed=11)
        session_start_event = events[0]
        page_view_event = events[1]
        
        # session_start should be first and at session start timestamp
        self.assertEqual(session_start_event.name, "session_start")
        self.assertEqual(session_start_event.timestamp_micros, session.start_timestamp_us)
        
        # session_start params should include session_id and session_number
        self.assertEqual(session_start_event.params["session_id"], session.session_id)
        self.assertEqual(session_start_event.params["session_number"], session.session_number)
        self.assertIn("language", session_start_event.params)
        self.assertIn("page_location", session_start_event.params)
        self.assertIn("page_title", session_start_event.params)
        
        # page_view should follow and have same session attributes
        self.assertEqual(page_view_event.name, "page_view")
        self.assertEqual(page_view_event.timestamp_micros, session.start_timestamp_us)
        self.assertEqual(page_view_event.params["session_id"], session_start_event.params["session_id"])
        self.assertEqual(page_view_event.params["session_number"], session_start_event.params["session_number"])


if __name__ == "__main__":
    unittest.main()
