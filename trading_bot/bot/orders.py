"""
Order placement logic layer.

Sits between the CLI and the BinanceClient:
  - Orchestrates validation → client call → response formatting
  - Returns structured OrderResult objects for clean output
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .client import BinanceClient, BinanceClientError
from .logging_config import get_logger
from .validators import validate_all

logger = get_logger("bot.orders")


@dataclass
class OrderResult:
    """Structured representation of a placed order response."""

    success: bool
    order_id: Optional[int] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    quantity: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    client_order_id: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "OrderResult":
        return cls(
            success=True,
            order_id=data.get("orderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            quantity=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            avg_price=data.get("avgPrice") or data.get("price"),
            price=data.get("price"),
            client_order_id=data.get("clientOrderId"),
            raw=data,
        )

    @classmethod
    def from_error(cls, error_code: int, error_message: str) -> "OrderResult":
        return cls(success=False, error_code=error_code, error_message=error_message)

    def summary_lines(self) -> list[str]:
        """Return a list of display-ready lines describing this result."""
        if not self.success:
            return [
                "─" * 50,
                "  ✗  ORDER FAILED",
                f"  Code   : {self.error_code}",
                f"  Reason : {self.error_message}",
                "─" * 50,
            ]

        lines = [
            "─" * 50,
            "  ✓  ORDER PLACED SUCCESSFULLY",
            f"  Order ID       : {self.order_id}",
            f"  Client Order ID: {self.client_order_id}",
            f"  Symbol         : {self.symbol}",
            f"  Side           : {self.side}",
            f"  Type           : {self.order_type}",
            f"  Status         : {self.status}",
            f"  Quantity       : {self.quantity}",
            f"  Executed Qty   : {self.executed_qty}",
            f"  Avg Price      : {self.avg_price or 'N/A'}",
        ]
        if self.order_type == "LIMIT":
            lines.append(f"  Limit Price    : {self.price}")
        lines.append("─" * 50)
        return lines


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
    reduce_only: bool = False,
) -> OrderResult:
    """
    Validate inputs and place an order via BinanceClient.

    Args:
        client:      Authenticated BinanceClient instance.
        symbol:      Trading pair symbol.
        side:        'BUY' or 'SELL'.
        order_type:  'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:    Order quantity.
        price:       Limit price (LIMIT orders).
        stop_price:  Stop trigger (STOP_MARKET orders).
        reduce_only: Only reduce existing position.

    Returns:
        OrderResult dataclass (success or failure).
    """
    # 1. Validate all inputs
    try:
        validated = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        logger.warning("Validation error: %s", exc)
        return OrderResult.from_error(error_code=-1, error_message=str(exc))

    logger.info(
        "Order request | symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
        validated["symbol"],
        validated["side"],
        validated["order_type"],
        validated["quantity"],
        validated["price"] or "N/A",
        validated["stop_price"] or "N/A",
    )

    # 2. Call the API
    try:
        response = client.place_order(
            symbol=validated["symbol"],
            side=validated["side"],
            order_type=validated["order_type"],
            quantity=validated["quantity"],
            price=validated["price"],
            stop_price=validated["stop_price"],
            reduce_only=reduce_only,
        )
        return OrderResult.from_response(response)

    except BinanceClientError as exc:
        logger.error("BinanceClientError: code=%s msg=%s", exc.code, exc.message)
        return OrderResult.from_error(error_code=exc.code, error_message=exc.message)

    except Exception as exc:
        logger.exception("Unexpected error placing order: %s", exc)
        return OrderResult.from_error(error_code=-99, error_message=str(exc))
