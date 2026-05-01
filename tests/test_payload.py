import unittest

from payload.builder import build_event_payload, make_page_view_event


class PayloadTests(unittest.TestCase):
    def test_build_event_payload(self):
        payload = build_event_payload(
            client_id="1234567890.1234567890",
            user_id="user_12345",
            events=[make_page_view_event({"session_id": 1, "session_number": 1, "engagement_time_msec": 100, "page_location": "https://example.com", "page_title": "Home"})],
        )
        self.assertEqual(payload["client_id"], "1234567890.1234567890")
        self.assertEqual(payload["user_id"], "user_12345")
        self.assertIn("events", payload)
        self.assertEqual(payload["events"][0]["name"], "page_view")


if __name__ == "__main__":
    unittest.main()
