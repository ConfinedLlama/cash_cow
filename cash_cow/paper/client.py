"""Small allowlisted HTTP adapter. No redirects or automatic POST retries."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

import requests

from cash_cow.intraday.data import read_keys

PAPER_URL = "https://paper-api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"


class APIError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Alpaca request failed (HTTP {status}); response body withheld")


class TransportError(RuntimeError):
    pass


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    return result


def iso(value):
    return value.astimezone(timezone.utc).isoformat()


class PaperClient:
    def __init__(self, headers=None, session=None):
        self.headers = read_keys() if headers is None else headers
        self.session = session or requests.Session()
        self.session.trust_env = False

    def request(self, method, path, *, params=None, body=None, data=False):
        allowed = (
            method == "GET" and path in {
                "/v2/account", "/v2/clock", "/v2/calendar", "/v2/positions",
                "/v2/orders", "/v2/orders:by_client_order_id", "/v2/assets/SPY",
            }
        ) or (method == "POST" and path == "/v2/orders") or (
            method == "DELETE" and re.fullmatch(r"/v2/orders/[a-fA-F0-9-]{36}", path)
        )
        if data:
            allowed = method == "GET" and path in {"/v2/stocks/bars", "/v2/stocks/quotes/latest", "/v1beta1/news"}
        if not allowed:
            raise ValueError("Endpoint is outside the paper runner allowlist")
        try:
            response = self.session.request(
                method, (DATA_URL if data else PAPER_URL) + path,
                headers=self.headers, params=params, json=body,
                timeout=(5, 15), allow_redirects=False,
            )
        except requests.RequestException:
            raise TransportError("Alpaca transport failed; order outcome may be unknown") from None
        if not 200 <= response.status_code < 300:
            raise APIError(response.status_code)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError:
            raise TransportError("Invalid Alpaca JSON; order outcome may be unknown") from None

    def account(self):
        return self.request("GET", "/v2/account")

    def clock(self):
        return self.request("GET", "/v2/clock")

    def calendar(self, day):
        return self.request("GET", "/v2/calendar", params={"start": str(day), "end": str(day)})

    def positions(self):
        return self.request("GET", "/v2/positions")

    def open_orders(self):
        rows = self.request("GET", "/v2/orders", params={"status": "open", "limit": 500})
        if len(rows) >= 500:
            raise ValueError("Order inventory may be truncated")
        return rows

    def asset(self):
        return self.request("GET", "/v2/assets/SPY")

    def order(self, client_id):
        try:
            return self.request("GET", "/v2/orders:by_client_order_id", params={"client_order_id": client_id})
        except APIError as error:
            if error.status == 404:
                return None
            raise

    def submit(self, payload):
        return self.request("POST", "/v2/orders", body=payload)

    def cancel(self, order_id):
        return self.request("DELETE", f"/v2/orders/{order_id}")

    def quote(self, feed):
        return self.request("GET", "/v2/stocks/quotes/latest", data=True,
                            params={"symbols": "SPY", "feed": feed})["quotes"]["SPY"]

    def news_page(self, start, end, token=None):
        params = {"start": iso(start), "end": iso(end), "limit": 50,
                  "sort": "asc", "include_content": "false"}
        if token:
            params["page_token"] = token
        return self.request("GET", "/v1beta1/news", data=True, params=params)

    def bars(self, start, now, feed):
        # Request only the present session; preserve the historical holdout.
        end = now.replace(second=0, microsecond=0) - timedelta(microseconds=1)
        if end < start:
            return []
        rows, tokens = [], set()
        params = {"symbols": "SPY", "timeframe": "1Min", "start": iso(start),
                  "end": iso(end), "feed": feed, "adjustment": "raw", "limit": 10000, "sort": "asc"}
        while True:
            response = self.request("GET", "/v2/stocks/bars", params=params, data=True)
            rows.extend((response.get("bars") or {}).get("SPY", []) or [])
            token = response.get("next_page_token")
            if not token:
                return rows
            if token in tokens:
                raise ValueError("Repeated market-data page token")
            tokens.add(token)
            params["page_token"] = token
