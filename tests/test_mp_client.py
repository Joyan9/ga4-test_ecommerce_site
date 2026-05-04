import unittest
from unittest.mock import AsyncMock, patch

from sender.mp_client import MPClient


class MPClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_429_then_success(self):
        client = MPClient("G-TEST", "SECRET", rps=100, use_debug=True)
        response_429 = type("Resp", (), {"status_code": 429})()
        response_200 = type("Resp", (), {"status_code": 200, "json": lambda self=None: {"validationMessages": []}, "text": "{}"})()

        with patch.object(client._client, "post", new=AsyncMock(side_effect=[response_429, response_200])) as mock_post:
            response = await client.send({"client_id": "1.1", "events": []})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_post.await_count, 2)

        await client.close()

    async def test_debug_validation_messages_are_supported(self):
        client = MPClient("G-TEST", "SECRET", rps=100, use_debug=True)
        response_200 = type(
            "Resp",
            (),
            {
                "status_code": 200,
                "text": '{"validationMessages": [{"fieldPath":"events[0].name","description":"Missing event name","validationCode":"VALUE_INVALID"}]}',
                "json": lambda self=None: {
                    "validationMessages": [
                        {
                            "fieldPath": "events[0].name",
                            "description": "Missing event name",
                            "validationCode": "VALUE_INVALID",
                        }
                    ]
                },
            },
        )()

        with patch.object(client._client, "post", new=AsyncMock(return_value=response_200)) as mock_post:
            response = await client.send({"client_id": "1.1", "events": []})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_post.await_count, 1)

        await client.close()

    def test_batch_by_client(self):
        payloads = [
            {"client_id": "a", "events": [{"name": "page_view", "params": {}}]},
            {"client_id": "a", "events": [{"name": "purchase", "params": {}}]},
            {"client_id": "b", "events": [{"name": "page_view", "params": {}}]},
        ]
        batched = MPClient.batch_by_client(payloads, max_events_per_request=25)
        self.assertEqual(len(batched), 2)
        self.assertEqual(sum(len(p["events"]) for p in batched), 3)


if __name__ == "__main__":
    unittest.main()
