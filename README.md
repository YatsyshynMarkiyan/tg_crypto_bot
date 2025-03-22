# Crypto Price Tracking Telegram Bot

---

## 📌 Project Overview

This project is a Telegram bot designed to track cryptocurrency prices from various sources, allowing users to monitor and receive alerts when their favorite tokens change in value. The bot supports multiple price providers, including Binance, CoinGecko, CoinMarketCap, ByBit, and OKX.

Users can:

- Get real-time cryptocurrency prices.
- Add and remove favorite tokens.
- Select a preferred price source.
- Receive alerts when a token's price changes significantly.
- View their saved favorite tokens with the latest prices.
- Clear the chat and cancel ongoing operations.

---

## ⚙️ Features

### 🔹 Main Features

- **Multi-Source Price Tracking**: Fetch prices from Binance, CoinGecko, CoinMarketCap, ByBit, and OKX.
- **Favorites Management**: Add and remove cryptocurrencies from a personalized watchlist.
- **Real-Time Alerts**: Receive notifications when a token's price changes by more than 5%.
- **Chat Management**: Clear messages and cancel ongoing commands.
- **Inline Keyboards**: Easily select sources and view token lists interactively.
- **Asynchronous Performance**: Uses `asyncio` for non-blocking API requests and event handling.

---

## 🚀 Setup & Installation

### 1️⃣ Prerequisites

Ensure you have the following installed:

- Python 3.8+
- Telegram Bot API Token (Create a bot via [BotFather](https://t.me/BotFather))
- API Keys (For CoinMarketCap, if used)

### 2️⃣ Clone the Repository

```bash
$ git clone https://github.com/your-username/crypto-telegram-bot.git
$ cd crypto-telegram-bot
```

### 3️⃣ Install Dependencies

Create a virtual environment (optional but recommended):

```bash
$ python -m venv venv
$ source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install required dependencies:

```bash
$ pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables

Create a `.env` file in the root directory and add:

```ini
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
CMC_API_KEY=your-coinmarketcap-api-key
```

### 5️⃣ Run the Bot

```bash
$ python bot.py
```

The bot will start polling for messages.

---

## 📌 Usage Guide

### ✅ Available Commands

| Command       | Description                                         |
|--------------|-----------------------------------------------------|
| `/start`     | Shows bot features and available commands.         |
| `/sources`   | Choose a cryptocurrency price source.             |
| `/add <symbol>` | Add a cryptocurrency to favorites.             |
| `/remove <symbol>` | Remove a cryptocurrency from favorites.     |
| `/list`      | View favorite tokens with current prices.          |
| `/clear`     | Delete recent messages (private chats only).       |
| `/cancel`    | Cancel the current action.                         |

### 📌 Getting Prices

Simply type a cryptocurrency symbol (e.g., BTC, ETH, DOGE) in the chat, and the bot will fetch the price from the active source.

### 🔔 Price Change Alerts

- The bot automatically checks price changes every 5 minutes.
- If a token price changes by more than 5%, the user receives a notification.

## 🏗️ Project Structure

```
crypto-telegram-bot/
│── bot.py                 # Main bot logic and message handling
│── database.py            # SQLite database management
│── tokens_list.py         # Fetching available trading pairs from exchanges
│── utils.py               # Helper functions
│── requirements.txt       # Python dependencies
│── README.md              # Project documentation
│── .env                   # Environment variables (not included in repo)
```

---

## 🔧 API Sources & Integrations

- **Binance API** - [Binance](https://api.binance.com/api/v3/ticker/price)
- **CoinGecko API** - [CoinGecko](https://api.coingecko.com/api/v3/simple/price)
- **CoinMarketCap API** - [CoinMarketCap](https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest)
- **ByBit API** - [ByBit](https://api.bybit.com/v5/market/tickers?category=spot)
- **OKX API** - [OKX](https://www.okx.com/api/v5/market/ticker?instId=TOKEN-USDT)

---

## Demo screns

## 🖼️ Screenshots

Here are some example screenshots from the project:

![Screenshot 1](screens/Знімок%20екрана%202025-03-22%20104009.png)
![Screenshot 2](screens/Знімок%20екрана%202025-03-22%20104017.png)
![Screenshot 3](screens/Знімок%20екрана%202025-03-22%20104025.png)
![Screenshot 4](screens/Знімок%20екрана%202025-03-22%20104035.png)
![Screenshot 5](screens/Знімок%20екрана%202025-03-22%20104044.png)
![Screenshot 6](screens/Знімок%20екрана%202025-03-22%20104054.png)
![Screenshot 7](remove.png)
![Screenshot 8](screens/Знімок%20екрана%202025-03-22%20104113.png)
![Screenshot 9](screens/Знімок%20екрана%202025-03-22%20104126.png)


---

## 💡 Future Improvements

✅ Add support for more cryptocurrency exchanges.

✅ Implement user-defined price alert thresholds.

✅ Webhook support for faster price updates.

✅ Multi-language support.

---

## 🤝 Contributing

Feel free to fork this repository, submit pull requests, or report issues.

---
