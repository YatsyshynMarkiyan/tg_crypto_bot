import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

def get_all_trading_pairs():
    """
    Fetches available trading pairs from multiple cryptocurrency data sources.

    Supported sources:
    - Binance
    - CoinGecko
    - CoinMarketCap
    - ByBit
    - OKX

    Returns:
        dict: A dictionary where keys are exchange names and values are sets of trading pairs.
    """

    # Define API endpoints for each source
    sources = {
        "Binance": "https://api.binance.com/api/v3/ticker/price",
        "CoinGecko": "https://api.coingecko.com/api/v3/coins/list",
        "CoinMarketCap": "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map",
        "ByBit": "https://api.bybit.com/v5/market/tickers?category=spot",
        "OKX": "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    }

    # API headers (needed only for CoinMarketCap)
    headers = {
        "CoinMarketCap": {"X-CMC_PRO_API_KEY": os.getenv("CMC_API_KEY")}
    }

    trading_pairs = {}  # Dictionary to store trading pairs for each source

    for source, url in sources.items():
        try:
            logging.info(f"🔄 Fetching trading pairs from {source}...")
            
            # Send request to the API
            response = requests.get(url, headers=headers.get(source, {}), timeout=15)

            # Check if the request was successful
            if response.status_code != 200:
                logging.warning(f"⚠ {source}: Failed to fetch data (Status Code: {response.status_code})")
                continue

            data = response.json()  # Parse JSON response
            logging.debug(f"📥 Response from {source}: {data}")

            # Process response data based on the source
            if source == "Binance":
                trading_pairs[source] = {
                    item["symbol"].replace("USDT", "") for item in data if item["symbol"].endswith("USDT")
                }

            elif source == "CoinGecko":
                if isinstance(data, list):
                    trading_pairs[source] = {item["symbol"].upper() for item in data}
                else:
                    logging.warning("⚠ CoinGecko returned an unexpected response format!")

            elif source == "CoinMarketCap":
                trading_pairs[source] = {item["symbol"] for item in data.get("data", [])}

            elif source == "ByBit":
                trading_pairs[source] = {
                    item["symbol"].replace("USDT", "") for item in data.get("result", {}).get("list", []) if item["symbol"].endswith("USDT")
                }

            elif source == "OKX":
                trading_pairs[source] = {
                    item["instId"].replace("-USDT", "") for item in data.get("data", []) if item["instId"].endswith("-USDT")
                }

            logging.info(f"✅ Retrieved {len(trading_pairs.get(source, []))} pairs from {source}")

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Request error while fetching from {source}: {e}")
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"❌ Error processing data from {source}: {e}")

    total_pairs = sum(len(v) for v in trading_pairs.values())
    logging.info(f"✅ Successfully loaded {total_pairs} trading pairs")

    return trading_pairs