# Binance Futures Testnet Trading Bot

A Python CLI application for placing orders on Binance Testnet.

## Project Structure
trading_bot/
bot/
client.py        # Binance REST client
orders.py        # Order placement logic
validators.py    # Input validation
logging_config.py
cli.py             # CLI entry point
logs/              # Log files
.env.example       # Credentials template
requirements.txt
## Setup

1. Clone the repository
2. Create virtual environment:
   python -m venv venv
   venv\Scripts\activate
3. Install dependencies:
   pip install -r requirements.txt
4. Copy .env.example to .env and add your API keys:
   BINANCE_API_KEY=your_key_here
   BINANCE_API_SECRET=your_secret_here

## How to Run

Market BUY:
   python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit SELL:
   python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 80000

Stop-Market (Bonus):
   python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 95000

View account:
   python cli.py account

List open orders:
   python cli.py open-orders --symbol BTCUSDT

## Assumptions
- Spot Testnet (testnet.binance.vision) used for testing as Futures Testnet requires GitHub authentication. Bot architecture is identical for Futures - only base URL and endpoints differ.
- Quantity must meet minimum notional value of $100
- timeInForce defaults to GTC for LIMIT orders
