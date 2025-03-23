import logging
import requests
import asyncio
from aiogram.exceptions import TelegramForbiddenError
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.types import CallbackQuery as CQ
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatType
from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from databse import Database
from tokens_list import get_all_trading_pairs
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

keep_alive()

load_dotenv()

# Your Telegram bot token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Bot initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()
router = Router()
logging.basicConfig(level=logging.INFO)

async def set_bot_commands(bot: Bot):
    """
    Function to set the list of available bot commands.
    This helps users understand what commands they can use with the bot.
    """
    commands = [
        BotCommand(command="start", description="Show bot features and commands"),
        BotCommand(command="sources", description="Select a price source"),
        BotCommand(command="add", description="Add a token to favorites"),
        BotCommand(command="remove", description="Remove a favorite token"),
        BotCommand(command="list", description="View favorite tokens with prices"),
        BotCommand(command="clear", description="Delete chat messages"),
        BotCommand(command="cancel", description="Cancel the current action"),
    ]
    await bot.set_my_commands(commands)

# Dictionary to store trading pairs data
trading_pairs = {}

async def update_trading_pairs_periodically():
    """
    Function to automatically update trading pairs every 10 minutes.
    It fetches the latest trading pairs from the data source.
    """
    while True:
        await get_all_trading_pairs()  # Update the list of trading pairs
        await asyncio.sleep(600)  # Update every 10 minutes (600 seconds)


def get_favorites_keyboard(user_id):
    """
    Generates an inline keyboard with the user's favorite tokens and their prices.
    If there are no valid tokens, it returns None.
    """
    active_source = db.get_active_source(user_id)  # Retrieve the user's active price source
    favorite_tokens = db.get_favorites(user_id, active_source)  # Retrieve favorite tokens for the source

    if not favorite_tokens:  # If the list is empty, return None
        return None

    buttons = []

    for token in favorite_tokens:
        price = get_price(token, user_id)  # Get the price from the selected source
        if price in ["Pair does not exist", "Error retrieving price"]:  # Skip invalid tokens
            continue
        display_price = f"${price}" if isinstance(price, (int, float)) else "❌"
        buttons.append([InlineKeyboardButton(text=f"{token} | {display_price}", callback_data=f"fav_{token}")])

    if not buttons:  # If all tokens were invalid, return None
        return None

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_price(symbol, user_id):
    """
    Retrieves the price of 'symbol' for the user 'user_id' from the active price source.
    CoinGecko is queried using ids={symbol.lower()} (without get_coin_id).
    """
    global trading_pairs
    source = db.get_active_source(user_id)

    logging.info(f"🔍 Fetching price for '{symbol}' from source '{source}'")

    # Ensure trading pairs are loaded and the source key exists
    if not trading_pairs or source not in trading_pairs:
        logging.warning(f"⚠ No trading pair data available for {source}")
        return "Error retrieving price"

    # Check if the trading pair exists in the source
    if symbol.upper() not in trading_pairs[source]:
        logging.warning(f"⚠ Pair {symbol} not found in {source}")
        return "Pair does not exist"

    # Define API endpoints for different price sources
    sources = {
        "Binance": f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}USDT",
        "CoinGecko": f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd",
        "CoinMarketCap": f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={symbol.upper()}&convert=USD",
        "ByBit": "https://api.bybit.com/v5/market/tickers?category=spot",
        "OKX": f"https://www.okx.com/api/v5/market/ticker?instId={symbol.upper()}-USDT"
    }

    # Set API headers if using CoinMarketCap (requires an API key)
    headers = {"X-CMC_PRO_API_KEY": os.getenv("CMC_API_KEY")} if source == "CoinMarketCap" else {}

    # Log the request URL
    request_url = sources[source]
    logging.debug(f"📡 Requesting data from {source}: {request_url}")

    try:
        # Send an API request
        response = requests.get(request_url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for non-200 responses
        data = response.json()

        logging.debug(f"📥 Response from {source}: {data}")

        # Process data based on the selected price source
        if source == "Binance":
            price = float(data.get("price", 0))
            logging.info(f"✅ Binance: {symbol} price = {price}")
            return price

        elif source == "CoinGecko":
            # Check if the symbol exists in the response data
            if symbol.lower() in data and "usd" in data[symbol.lower()]:
                price = float(data[symbol.lower()]["usd"])
                logging.info(f"✅ CoinGecko: {symbol} price = {price}")
                return price
            else:
                logging.warning(f"⚠ CoinGecko: '{symbol.lower()}' not found in the response.")

        elif source == "CoinMarketCap":
            price = float(data["data"].get(symbol.upper(), {}).get("quote", {}).get("USD", {}).get("price", 0))
            logging.info(f"✅ CoinMarketCap: {symbol} price = {price}")
            return price

        elif source == "ByBit":
            url = "https://api.bybit.com/v5/market/tickers?category=spot"

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()  # Raise an error if status is not 200
                data = response.json()

                if data["retCode"] != 0:
                    logging.error(f"❌ ByBit API error: {data}")
                    return "Error retrieving price"

                # Search for the token in the trading pairs list
                for ticker in data["result"]["list"]:
                    if ticker["symbol"] == f"{symbol.upper()}USDT":
                        return float(ticker["lastPrice"])

                return "Pair does not exist"

            except requests.exceptions.RequestException as e:
                logging.error(f"❌ Request error to {source} for {symbol}: {e}")
                return "Error retrieving price"

        elif source == "OKX":
            if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                price = float(data["data"][0].get("last", 0))
                logging.info(f"✅ OKX: {symbol} price = {price}")
                return price

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Request error from {source} for {symbol}: {e}")
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"❌ Invalid response from {source} for {symbol}: {e}")

    # Return an error message if price retrieval fails
    logging.warning(f"⚠ Returning 'Error retrieving price' for {symbol} from {source}")
    return "Error retrieving price"

async def check_price_changes():
    """
    Monitors price changes for favorite tokens and notifies users if the price change exceeds 5%.
    Runs continuously in a loop with a 5-minute interval.
    """
    while True:
        users = db.get_all_users()  # Retrieve the list of users
        for user_id in users:
            active_source = db.get_active_source(user_id)  # Get the user's selected data source
            tokens = db.get_favorites(user_id, active_source)  # Retrieve favorite tokens for this source

            for token in tokens:
                old_price = db.get_last_price(user_id, token, active_source)  # Get the last recorded price
                new_price = get_price(token, user_id)  # Fetch the latest price

                # Skip invalid or non-existent pairs
                if isinstance(new_price, str) or new_price in ["Pair does not exist", "Error retrieving price"]:
                    continue  

                new_price = float(new_price)

                # Notify user if the price change exceeds 5%
                if old_price is not None and abs(new_price - old_price) / old_price * 100 > 5:
                    try:
                        await bot.send_message(
                            user_id,
                            f"🚨 {token} has changed price on {active_source}!\n"
                            f"📉 Old price: ${old_price:.2f}\n"
                            f"📈 New price: ${new_price:.2f}"
                        )
                        # Update the last recorded price in the database
                        db.update_last_price(user_id, token, new_price, active_source)
                    except TelegramForbiddenError:
                        logging.warning(f"❌ Could not send a message to user {user_id}, possibly blocked the bot.")

        await asyncio.sleep(300)  # Check price changes every 5 minutes

@router.message(Command("start"))
async def start_command(message: Message):
    """
    Sends a welcome message and provides an overview of the bot's functionality.
    """
    text = (
        "👋 Welcome! I am a bot for tracking cryptocurrency prices.\n\n"
        "📌 Main Commands:\n"
        "🔹 `/sources` — Select a data source (Binance, CoinGecko, ByBit, etc.)\n"
        "🔹 `/add <symbol>` — Add a cryptocurrency to your favorites list\n"
        "🔹 `/remove <symbol>` — Remove a cryptocurrency from your favorites list\n"
        "🔹 `/list` — View your favorite tokens and their prices\n"
        "🔹 `/cancel` — Cancel the current action\n"
        "🔹 `/clear` — Clear chat history\n\n"
        "📊 Select a command and start using the bot!"
    )

    await message.answer(text)

@router.message(F.text, ~F.text.startswith("/"))
async def get_crypto_price(message: Message):
    """
    Retrieves the price of a cryptocurrency entered by the user from the selected data source.
    Ignores messages that start with "/".
    """
    user_id = message.from_user.id
    symbol = message.text.strip().upper()

    # Ignore commands (messages starting with "/")
    if symbol.startswith("/"):
        return

    # Get the user's active data source
    active_source = db.get_active_source(user_id)

    # Retrieve the price of the entered token
    price = get_price(symbol, user_id)

    if price in ["Pair does not exist", "Error retrieving price"]:
        await message.reply(f"⚠ `{symbol}` was not found on `{active_source}`. Please enter another token.")
    else:
        await message.reply(f"💰 `{symbol}` on `{active_source}`: `${price}`")

@router.message(Command("clear"))
async def clear_chat(message: Message):
    """
    🧹 Clears the chat by deleting recent messages from the user and the bot.
    Works only in private chats.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Ensure the command is used in a private chat
    if message.chat.type != ChatType.PRIVATE:
        await message.reply("❌ This command only works in a private chat with the bot!")
        return

    deleted_count = 0  # Counter for deleted messages
    last_message_id = message.message_id  # Start with the latest message ID

    try:
        # Attempt to delete the last 50 messages
        for msg_id in range(last_message_id, last_message_id - 50, -1):
            try:
                await bot.delete_message(chat_id, msg_id)
                deleted_count += 1
            except TelegramBadRequest:
                continue  # Ignore errors if the message cannot be deleted

        # Confirm deletion if messages were removed
        if deleted_count > 0:
            confirmation = await message.answer(f"🧹 {deleted_count} messages deleted!")
            await asyncio.sleep(2)  # Wait 2 seconds before deleting confirmation message
            await confirmation.delete()
        else:
            await message.reply("ℹ No messages to delete!")

    except TelegramForbiddenError:
        await message.reply("⚠ The bot does not have permission to delete messages!")
    except Exception as e:
        logging.error(f"❌ Error while clearing chat: {e}")
        await message.reply("❌ Failed to clear chat. Ensure the bot has the necessary permissions.")

@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):
    """
    Cancels the user's current action and clears the FSM state.
    """
    
    # Get the current FSM state
    current_state = await state.get_state()

    if current_state is None:
        await message.reply("ℹ You have no active actions to cancel.")
    else:
        # Clear the state
        await state.clear()
        await message.reply("✅ Your current action has been canceled. You may continue using the bot.")

@router.message(Command('add'))
async def add_favorite(message: Message):
    """
    Adds a cryptocurrency to the user's favorites list.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❗ Please specify a token symbol! Example: `/add BTC`")
        return

    symbol = args[1].strip().upper()
    if not symbol.isalnum():
        await message.reply("⚠ Invalid token symbol. Only letters and numbers are allowed!")
        return

    user_id = message.from_user.id
    active_source = db.get_active_source(user_id)  # Get the selected data source
    
    price = get_price(symbol, user_id)
    if price in ["Pair does not exist", "Error retrieving price", None]: 
        await message.reply(f"⚠ The pair `{symbol}` does not exist on {active_source}. Please enter a different token.")
        return

    # Retrieve the user's favorite tokens from the selected source
    favorites = db.get_favorites(user_id, active_source)

    if symbol in favorites:
        await message.reply(f"ℹ `{symbol}` is already in your favorites list ({active_source})!")
    else:
        db.add_favorite(user_id, symbol, active_source)  # Add token to favorites
        await message.reply(f"✅ `{symbol}` has been added to your favorites on `{active_source}`!\n💰 Current price: `${price}`")

@router.message(Command('remove'))
async def remove_favorite(message: Message):
    """
    Removes a cryptocurrency from the user's favorites list.
    """
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Please specify a token symbol! Example: `/remove BTC`")
        return

    symbol = args[1].upper()
    user_id = message.from_user.id
    active_source = db.get_active_source(user_id)  # Retrieve the selected data source

    db.remove_favorite(user_id, symbol, active_source)  # Remove token only from this source
    await message.reply(f"✅ `{symbol}` has been removed from your favorites on `{active_source}`!")


# 🔹 Create a state for waiting for token input
class TokenState(StatesGroup):
    waiting_for_token = State()

@router.message(Command('list'))
async def send_favorites(message: Message, state: FSMContext):
    """
    Displays the list of favorite tokens for the selected data source.
    If there are no favorites, prompts the user to enter a token.
    """
    user_id = message.from_user.id
    active_source = db.get_active_source(user_id)  # Retrieve the active source
    keyboard = get_favorites_keyboard(user_id)  # Retrieve the tokens for this source

    if not keyboard:
        await message.reply(f"📊 Your active source: {active_source}\n⚠ No favorite tokens found for this source. Please enter a token:")
    else:
        await message.reply(f"📊 Your active source: {active_source}\n🔽 Select a token or enter a new one:", reply_markup=keyboard)

    await state.set_state(TokenState.waiting_for_token)  # Set the state

@router.message(TokenState.waiting_for_token)
async def process_token_input(message: Message, state: FSMContext):
    """
    Processes the user's token input, retrieves its price from the active source,
    and either displays the price or adds it to favorites if not already added.
    """
    user_id = message.from_user.id
    token = message.text.strip().upper()
    active_source = db.get_active_source(user_id)
    price = get_price(token, user_id)

    if price == "The pair does not exist":  # If the token is not available on the active source
        await message.reply(f"⚠ `{token}` does not exist on `{active_source}`. Please enter another token:")
    elif price == "Error while getting price":  # If there was an error retrieving the price
        await message.reply("❌ Error retrieving price. Please try again:")
    else:
        if token in db.get_favorites(user_id, active_source):  # If token is already in favorites
            await message.reply(f"💰 `{token}` on `{active_source}`: `${price}`")
        else:
            db.add_favorite(user_id, token, active_source)  # Add token to favorites
            await message.reply(f"✅ `{token}` has been added to your favorites!\n💰 `{price}`")

    await state.clear()  # Clear the FSM state after processing


def get_active_source(user_id):
    """
    Retrieves the active data source for a given user.
    If no source is found, defaults to "Binance" and updates the database.
    """
    source = db.get_active_source(user_id)
    if source is None:
        db.update_active_source(user_id, "Binance")  # Set default source in DB
        return "Binance"
    return source


SOURCES = ["Binance", "CoinGecko", "CoinMarketCap", "ByBit", "OKX"]

@router.message(Command("sources"))
async def show_sources(message: Message):
    """
    Displays a list of available price sources.
    Deletes the previous message before sending a new one.
    """
    user_id = message.from_user.id
    active_source = db.get_active_source(user_id)

    # Generate inline keyboard with available sources and mark the active one
    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅ ' if src == active_source else ''}{src}",
            callback_data=f"source_{src}"
        )] 
        for src in SOURCES
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Retrieve the last message ID with the sources list from the database
    last_message_id = db.get_last_source_message(user_id)

    # Try to delete the old message before sending a new one
    if last_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_message_id)
        except TelegramBadRequest:
            logging.info("⚠ Could not delete the previous message (it may already be deleted or outdated).")

    # Send a new message with the sources list
    sent_message = await message.answer(
        text=f"📊 Your active source: `{active_source}`\nSelect a different source:",
        reply_markup=keyboard
    )
    
    # Update the last sent message ID in the database for this user
    db.update_last_source_message(user_id, sent_message.message_id)

@router.callback_query(F.data.startswith("source_"))
async def switch_source(call: CQ):
    """
    Changes the active price source and updates the source list in an already sent message.
    """
    user_id = call.from_user.id
    new_source = call.data.split("_", 1)[1]  # Extract the selected source name (e.g., Binance, ByBit, OKX)

    current_source = db.get_active_source(user_id)
    if new_source == current_source:
        # If the user selects the already active source, show an alert and do nothing
        await call.answer("ℹ This source is already active!", show_alert=True)
        return

    # Update the active source in the database
    db.update_active_source(user_id, new_source)
    
    # Confirm the source change with a popup message
    await call.answer(f"🔄 Source changed to {new_source}")

    # Generate updated keyboard with the new active source marked
    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅ ' if src == new_source else ''}{src}",
            callback_data=f"source_{src}"
        )] 
        for src in SOURCES
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    new_text = f"📊 Your active source: `{new_source}`\nSelect a different one:"

    # Try to edit the existing message with the updated source selection
    try:
        await call.message.edit_text(new_text, reply_markup=keyboard)
        # Update the last message ID in the database (remains the same in this case)
        db.update_last_source_message(user_id, call.message.message_id)
    except TelegramBadRequest as e:
        # If editing fails (e.g., message not found or outdated), send a new one
        logging.warning(f"⚠ Failed to update the source list message: {e}")
        new_msg = await call.message.answer(new_text, reply_markup=keyboard)
        db.update_last_source_message(user_id, new_msg.message_id)

async def update_trading_pairs():
    """
    Periodically updates the list of trading pairs every 10 minutes.
    """
    global trading_pairs
    while True:
        trading_pairs = get_all_trading_pairs()  # ✅ Updates the list of trading pairs
        print(f"✅ Updated list of trading pairs ({len(trading_pairs)} pairs)")
        await asyncio.sleep(600)  # Updates every 10 minutes

async def main():
    """
    Main function to start the bot and initialize necessary tasks.
    """
    global trading_pairs

    dp.include_router(router)  # Include router to the dispatcher

    logging.info("🔄 Loading trading pairs...")
    
    try:
        trading_pairs = get_all_trading_pairs()  # Fetch initial trading pairs
    except Exception as e:
        logging.error(f"❌ Error while fetching trading pairs: {e}")
        return

    if not trading_pairs:
        logging.error("❌ Error: The list of trading pairs is empty!")
        return

    print(f"✅ Loaded {sum(len(v) for v in trading_pairs.values())} trading pairs")

    asyncio.create_task(check_price_changes())  # Start monitoring price changes in the background
    asyncio.create_task(update_trading_pairs())  # Periodically update trading pairs

    await dp.start_polling(bot)  # Start polling the bot

if __name__ == "__main__":
    asyncio.run(main())