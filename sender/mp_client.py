import asyncio
from collections import defaultdict
from typing import Dict, Any, List, Iterable
import httpx
from loguru import logger


class MPClient:
    def __init__(self, measurement_id: str, api_secret: str, rps: float = 5.0, use_debug: bool = False):
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self.rps = rps
        self.use_debug = use_debug
        self._client = httpx.AsyncClient(timeout=30.0)
        self._last_call = 0.0

    def _endpoint(self) -> str:
        base = "https://www.google-analytics.com"
        path = "/debug/mp/collect" if self.use_debug else "/mp/collect"
        return f"{base}{path}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"

    @staticmethod
    def _format_validation_message(message: Dict[str, Any]) -> str:
        field_path = message.get("fieldPath", "<unknown>")
        description = message.get("description", "<no description>")
        code = message.get("validationCode", "<unknown>")
        return f"{code} at {field_path}: {description}"

    def _log_validation_messages(self, response: httpx.Response, client_id: str | None) -> None:
        if not self.use_debug:
            return

        try:
            body = response.json()
        except Exception:
            logger.warning(
                "GA4 debug response was not JSON client_id={} status_code={} body={}",
                client_id,
                response.status_code,
                response.text,
            )
            return

        messages = body.get("validationMessages", []) if isinstance(body, dict) else []
        if not messages:
            logger.info("GA4 debug validation passed client_id={} status_code={}", client_id, response.status_code)
            return

        for message in messages:
            logger.warning(
                "GA4 validation message client_id={} {}",
                client_id,
                self._format_validation_message(message),
            )

    async def send(self, payload: Dict[str, Any]) -> httpx.Response:
        url = self._endpoint()
        event_names = [event.get("name", "") for event in payload.get("events", [])]
        logger.debug(
            "Sending GA4 payload client_id={} event_count={} first_events={} endpoint={}",
            payload.get("client_id"),
            len(event_names),
            event_names[:5],
            url,
        )
        # rate limit
        now = asyncio.get_event_loop().time()
        min_interval = 1.0 / max(1.0, self.rps)
        wait = self._last_call + min_interval - now
        if wait > 0:
            logger.debug("Rate limiting GA4 request for {:.3f}s", wait)
            await asyncio.sleep(wait)
        # retries on 429/503
        backoff = 1.0
        for attempt in range(4):
            resp = await self._client.post(url, json=payload)
            self._last_call = asyncio.get_event_loop().time()
            logger.debug(
                "GA4 response attempt={} status_code={} client_id={} endpoint={}",
                attempt + 1,
                resp.status_code,
                payload.get("client_id"),
                url,
            )
            if resp.status_code in (429, 503):
                logger.warning(
                    "GA4 returned retryable status={} attempt={} client_id={} backoff={}",
                    resp.status_code,
                    attempt + 1,
                    payload.get("client_id"),
                    backoff,
                )
                if attempt == 3:
                    logger.error(
                        "GA4 request failed after retries client_id={} status_code={} body={}",
                        payload.get("client_id"),
                        resp.status_code,
                        resp.text,
                    )
                    return resp
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code >= 400:
                logger.error(
                    "GA4 returned non-success status client_id={} status_code={} body={}",
                    payload.get("client_id"),
                    resp.status_code,
                    resp.text,
                )
            self._log_validation_messages(resp, payload.get("client_id"))
            return resp
        return resp

    async def send_many(self, payloads: List[Dict[str, Any]]) -> List[httpx.Response]:
        responses: List[httpx.Response] = []
        for payload in payloads:
            responses.append(await self.send(payload))
        return responses

    @staticmethod
    def batch_by_client(payloads: Iterable[Dict[str, Any]], max_events_per_request: int = 25) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for payload in payloads:
            grouped[payload["client_id"]].append(payload)

        batched: List[Dict[str, Any]] = []
        for client_id, user_payloads in grouped.items():
            events_buffer: List[Dict[str, Any]] = []
            common_fields: Dict[str, Any] = {"client_id": client_id}
            for payload in user_payloads:
                common_fields.setdefault("user_id", payload.get("user_id"))
                common_fields.setdefault("timestamp_micros", payload.get("timestamp_micros"))
                common_fields.setdefault("user_properties", payload.get("user_properties"))
                if len(events_buffer) + len(payload.get("events", [])) > max_events_per_request and events_buffer:
                    batched.append({**common_fields, "events": events_buffer})
                    events_buffer = []
                events_buffer.extend(payload.get("events", []))
            if events_buffer:
                batched.append({**common_fields, "events": events_buffer})
        return batched

    async def close(self):
        await self._client.aclose()


__all__ = ["MPClient"]
