#!/usr/bin/env python3
"""
cli.py – Command-line interface for the Binance Futures Testnet trading bot.

Usage examples
--------------
# Market BUY
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500

# Stop-Market BUY (bonus order type)
python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000

# Check account balance
python cli.py account

# List open orders
python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import click
from dotenv import load_dotenv

# Ensure the package is importable when running from project root
sys.path.insert(0, os.path.dirname(__file__))

from bot.client import BinanceClient, BinanceClientError
from bot.logging_config import get_logger, setup_logging
from bot.orders import place_order

# ---------------------------------------------------------------------------
# Bootstrap logging before anything else
# ---------------------------------------------------------------------------
load_dotenv()
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("cli")

# ---------------------------------------------------------------------------
# Shared CLI context
# ---------------------------------------------------------------------------

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _make_client() -> BinanceClient:
    """Build a BinanceClient from environment variables."""
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        click.echo(
            click.style(
                "\n[ERROR] BINANCE_API_KEY and BINANCE_API_SECRET must be set "
                "in your environment or .env file.\n",
                fg="red",
                bold=True,
            ),
            err=True,
        )
        sys.exit(1)

    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """
    \b
    ╔══════════════════════════════════════════╗
    ║   Binance Futures Testnet Trading Bot    ║
    ╚══════════════════════════════════════════╝

    Credentials are read from environment variables or a .env file:
      BINANCE_API_KEY=<your key>
      BINANCE_API_SECRET=<your secret>
    """


# ---------------------------------------------------------------------------
# place command
# ---------------------------------------------------------------------------


@cli.command("place")
@click.option("--symbol", "-s", required=True, help="Trading pair, e.g. BTCUSDT")
@click.option(
    "--side",
    required=True,
    type=click.Choice(["BUY", "SELL"], case_sensitive=False),
    help="Order side.",
)
@click.option(
    "--type",
    "order_type",
    required=True,
    type=click.Choice(["MARKET", "LIMIT", "STOP_MARKET"], case_sensitive=False),
    help="Order type.",
)
@click.option("--quantity", "-q", required=True, type=float, help="Order quantity.")
@click.option("--price", "-p", default=None, type=float, help="Limit price (required for LIMIT).")
@click.option(
    "--stop-price",
    default=None,
    type=float,
    help="Stop trigger price (required for STOP_MARKET).",
)
@click.option(
    "--reduce-only",
    is_flag=True,
    default=False,
    help="Only reduce an existing position.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the order parameters without submitting.",
)
def place_cmd(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
    reduce_only: bool,
    dry_run: bool,
):
    """Place a new order on Binance Futures Testnet."""

    # ---------- Print request summary ----------
    click.echo("\n" + click.style("ORDER REQUEST SUMMARY", bold=True))
    click.echo("─" * 50)
    click.echo(f"  Symbol      : {symbol.upper()}")
    click.echo(f"  Side        : {side.upper()}")
    click.echo(f"  Type        : {order_type.upper()}")
    click.echo(f"  Quantity    : {quantity}")
    if price:
        click.echo(f"  Price       : {price}")
    if stop_price:
        click.echo(f"  Stop Price  : {stop_price}")
    if reduce_only:
        click.echo(f"  Reduce Only : True")
    if dry_run:
        click.echo(click.style("\n  [DRY RUN] Order not submitted.\n", fg="yellow"))
        logger.info("Dry run – order not submitted.")
        return
    click.echo("─" * 50)

    # ---------- Place order ----------
    client = _make_client()
    result = place_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        reduce_only=reduce_only,
    )

    # ---------- Print response ----------
    click.echo("\n" + click.style("ORDER RESPONSE", bold=True))
    for line in result.summary_lines():
        color = "green" if result.success else "red"
        click.echo(click.style(line, fg=color))

    if result.success:
        logger.info("CLI order success | orderId=%s", result.order_id)
        sys.exit(0)
    else:
        logger.error("CLI order failed | code=%s msg=%s", result.error_code, result.error_message)
        sys.exit(1)


# ---------------------------------------------------------------------------
# account command
# ---------------------------------------------------------------------------


@cli.command("account")
@click.option("--json-output", "json_output", is_flag=True, help="Print raw JSON response.")
def account_cmd(json_output: bool):
    """Display futures account information (balances)."""
    client = _make_client()
    try:
        info = client.get_account_info()
    except BinanceClientError as exc:
        click.echo(click.style(f"\n[ERROR] {exc}\n", fg="red"), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(click.style(f"\n[ERROR] {exc}\n", fg="red"), err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(info, indent=2))
        return

    click.echo("\n" + click.style("ACCOUNT INFORMATION", bold=True))
    click.echo("─" * 50)

    assets = [a for a in info.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    if not assets:
        click.echo("  No assets with non-zero balance found.")
    for asset in assets:
        click.echo(f"  {asset['asset']:<8} Wallet: {float(asset['walletBalance']):.4f}  "
                   f"Available: {float(asset.get('availableBalance', 0)):.4f}  "
                   f"UnrealizedPnL: {float(asset.get('unrealizedProfit', 0)):.4f}")

    click.echo("─" * 50)


# ---------------------------------------------------------------------------
# open-orders command
# ---------------------------------------------------------------------------


@cli.command("open-orders")
@click.option("--symbol", "-s", default=None, help="Filter by symbol (optional).")
@click.option("--json-output", "json_output", is_flag=True, help="Print raw JSON response.")
def open_orders_cmd(symbol: Optional[str], json_output: bool):
    """List all open orders (optionally filtered by symbol)."""
    client = _make_client()
    try:
        orders = client.get_open_orders(symbol=symbol.upper() if symbol else None)
    except BinanceClientError as exc:
        click.echo(click.style(f"\n[ERROR] {exc}\n", fg="red"), err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(orders, indent=2))
        return

    click.echo("\n" + click.style("OPEN ORDERS", bold=True))
    click.echo("─" * 70)
    if not orders:
        click.echo("  No open orders found.")
    for o in orders:
        click.echo(
            f"  [{o['orderId']}] {o['symbol']} | {o['side']} {o['type']} | "
            f"qty={o['origQty']} | price={o.get('price', 'N/A')} | status={o['status']}"
        )
    click.echo("─" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
