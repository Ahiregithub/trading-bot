"""
Input validation for order parameters.
All validation raises ValueError with human-readable messages.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}

# Binance symbol pattern: uppercase letters only, 2–20 chars
_SYMBOL_RE = re.compile(r"^[A-Z]{2,20}$")


def validate_symbol(symbol: str) -> str:
    """Normalise and validate a trading symbol (e.g. 'btcusdt' → 'BTCUSDT')."""
    symbol = symbol.strip().upper()
    if not _SYMBOL_RE.match(symbol):
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be 2-20 uppercase letters (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """Normalise and validate order side."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Normalise and validate order type."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> str:
    """Validate quantity is a positive number and return as string."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {quantity}.")
    return str(qty)


def validate_price(price: str | float | None, order_type: str) -> Optional[str]:
    """
    Validate price field.
    - Required for LIMIT and STOP_MARKET orders.
    - Must be a positive number.
    """
    if order_type == "MARKET":
        if price is not None:
            # Warn-only: price is ignored for MARKET orders
            return None
        return None

    # LIMIT / STOP_MARKET require a price
    if price is None:
        raise ValueError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {price}.")
    return str(p)


def validate_stop_price(stop_price: str | float | None, order_type: str) -> Optional[str]:
    """Validate stop price for STOP_MARKET orders."""
    if order_type != "STOP_MARKET":
        return None
    if stop_price is None:
        raise ValueError("Stop price (--stop-price) is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Invalid stop price '{stop_price}'. Must be a positive number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero, got {stop_price}.")
    return str(sp)


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """
    Run all validators and return a clean params dict.
    Raises ValueError on the first failure encountered.
    """
    validated = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type.upper()),
        "stop_price": validate_stop_price(stop_price, order_type.upper()),
    }
    return validated
