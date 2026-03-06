# Binance Futures Testnet Trading Bot

A clean, production-structured Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST client (signing, retries, HTTP)
│   ├── orders.py            # Order placement logic + OrderResult dataclass
│   ├── validators.py        # Input validation (raises ValueError)
│   └── logging_config.py   # Rotating file + console logging setup
├── cli.py                   # Click CLI entry point
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── .env.example             # Credentials template
├── requirements.txt
└── README.md
```

### Architectural Layers

| Layer | File | Responsibility |
|---|---|---|
| Transport | `bot/client.py` | HMAC signing, HTTP, retries, raw API |
| Business logic | `bot/orders.py` | Validate → call → format result |
| Validation | `bot/validators.py` | Pure input checks, raises `ValueError` |
| CLI | `cli.py` | User-facing commands, rich output |
| Logging | `bot/logging_config.py` | File + console handlers |

---

## Setup

### 1. Get Testnet Credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Navigate to **API Key** → generate a new key pair
4. Copy the API Key and Secret

### 2. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure Credentials

```bash
cp .env.example .env
```

Edit `.env`:
```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
LOG_LEVEL=INFO   # or DEBUG for verbose output
```

---

## Usage

### Place a Market Order

```bash
# Market BUY
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Market SELL
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

### Place a Limit Order

```bash
# Limit BUY
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 90000

# Limit SELL
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3500
```

### Place a Stop-Market Order *(bonus order type)*

```bash
python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000
```

### Dry Run (no order submitted)

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --dry-run
```

### View Account Balances

```bash
python cli.py account

# Raw JSON output
python cli.py account --json-output
```

### List Open Orders

```bash
python cli.py open-orders
python cli.py open-orders --symbol BTCUSDT
```

### Help

```bash
python cli.py --help
python cli.py place --help
```

---

## Example Output

```
ORDER REQUEST SUMMARY
──────────────────────────────────────────────────
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.001
──────────────────────────────────────────────────

ORDER RESPONSE
──────────────────────────────────────────────────
  ✓  ORDER PLACED SUCCESSFULLY
  Order ID       : 4798234
  Client Order ID: testbot_m_001
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Status         : FILLED
  Quantity       : 0.001
  Executed Qty   : 0.001
  Avg Price      : 96482.10
──────────────────────────────────────────────────
```

---

## Logging

All activity is logged to `logs/trading_bot.log` (rotating, max 5 MB × 3 files):

```
2025-07-10 14:22:01 | INFO     | bot.client           | BinanceClient initialised (base_url=https://testnet.binancefuture.com)
2025-07-10 14:22:01 | INFO     | bot.orders           | Order request | symbol=BTCUSDT side=BUY type=MARKET qty=0.001 price=N/A stop=N/A
2025-07-10 14:22:01 | DEBUG    | bot.client           | → POST /fapi/v1/order | params={...}
2025-07-10 14:22:01 | INFO     | bot.client           | Order placed | orderId=4798234 status=FILLED executedQty=0.001 avgPrice=96482.10
```

Set `LOG_LEVEL=DEBUG` in `.env` to see full request/response bodies.

---

## Error Handling

| Error Type | Handling |
|---|---|
| Invalid CLI input (bad quantity, missing price) | `ValueError` caught, friendly message printed, exit code 1 |
| Binance API errors (e.g. -2019 Insufficient margin) | `BinanceClientError` caught, code + message displayed |
| Network failures | `requests.RequestException` with automatic retry (3×) |
| Unexpected exceptions | Caught + logged with full traceback at `ERROR` level |

---

## Assumptions

- **Testnet only**: The base URL is hardcoded to `https://testnet.binancefuture.com`. Change `TESTNET_BASE_URL` in `client.py` for mainnet.
- **One-way position mode**: Orders use `positionSide=BOTH` (default). Hedge mode is not supported.
- **Quantity precision**: Passed as-is; Binance will reject invalid precision for a symbol. You can add per-symbol lot-size filtering as a future enhancement.
- **`timeInForce`**: Defaults to `GTC` for LIMIT orders.
- **No position management**: This bot places orders only; it does not track P&L or manage open positions.

---

## Requirements

- Python 3.10+
- See `requirements.txt` for dependencies
