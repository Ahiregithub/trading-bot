"""
Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Timestamping
  - HTTP session management with retries
  - Raw API calls with structured logging
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_config import get_logger

logger = get_logger("bot.client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3


class BinanceClientError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Only signed (private) endpoints are supported here;
    the client automatically injects timestamp + signature.
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._base_url = base_url.rstrip("/")

        self._session = self._build_session()
        logger.info("BinanceClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _sign(self, params: Dict[str, Any]) -> str:
        """Return HMAC-SHA256 hex signature for the given params dict."""
        query_string = urlencode(params)
        signature = hmac.new(self._api_secret, query_string.encode(), hashlib.sha256).hexdigest()
        return signature

    def _headers(self) -> Dict[str, str]:
        return {"X-MBX-APIKEY": self._api_key, "Content-Type": "application/x-www-form-urlencoded"}

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request against the Binance API.

        Args:
            method:   HTTP verb ('GET', 'POST', 'DELETE').
            endpoint: API path starting with '/'.
            params:   Query / body parameters.
            signed:   Whether to attach timestamp + signature.

        Returns:
            Parsed JSON response dict.

        Raises:
            BinanceClientError: On API-level errors.
            requests.RequestException: On network-level failures.
        """
        params = params or {}

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)

        url = f"{self._base_url}{endpoint}"

        logger.debug(
            "→ %s %s | params=%s",
            method,
            endpoint,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    headers=self._headers(),
                    timeout=DEFAULT_TIMEOUT,
                )
            else:
                response = self._session.request(
                    method,
                    url,
                    data=params,
                    headers=self._headers(),
                    timeout=DEFAULT_TIMEOUT,
                )
        except requests.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise
        except requests.Timeout:
            logger.error("Request timed out after %ss", DEFAULT_TIMEOUT)
            raise

        logger.debug("← HTTP %s | body=%s", response.status_code, response.text[:500])

        data = response.json()

        # Binance signals errors via a top-level "code" < 0
        if isinstance(data, dict) and data.get("code", 0) < 0:
            logger.error(
                "API error | code=%s msg=%s", data.get("code"), data.get("msg")
            )
            raise BinanceClientError(code=data["code"], message=data.get("msg", "Unknown error"))

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self._request("GET", "/fapi/v1/time", signed=False)
        return data["serverTime"]

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch futures account information."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures Testnet.

        Args:
            symbol:        Trading pair (e.g. 'BTCUSDT').
            side:          'BUY' or 'SELL'.
            order_type:    'MARKET', 'LIMIT', or 'STOP_MARKET'.
            quantity:      Order quantity as string.
            price:         Limit price (required for LIMIT).
            stop_price:    Stop trigger price (required for STOP_MARKET).
            time_in_force: 'GTC', 'IOC', or 'FOK' (LIMIT only).
            reduce_only:   Whether the order should only reduce position.

        Returns:
            Raw Binance order response dict.
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            if not price:
                raise ValueError("price is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = time_in_force

        if order_type == "STOP_MARKET":
            if not stop_price:
                raise ValueError("stopPrice is required for STOP_MARKET orders.")
            params["stopPrice"] = stop_price

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing order | symbol=%s side=%s type=%s qty=%s price=%s",
            symbol,
            side,
            order_type,
            quantity,
            price or stop_price or "N/A",
        )

        response = self._request("POST", "/fapi/v1/order", params=params)

        logger.info(
            "Order placed | orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )

        return response

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order | symbol=%s orderId=%s", symbol, order_id)
        return self._request("DELETE", "/fapi/v1/order", params=params)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """List open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)
