import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

# Import configurations and handlers
try:
    from .config import BOT_TOKEN
    from .handlers import router as main_router
except ImportError:
    # This is to handle the case where the script is run directly for testing
    # and the relative imports might not work as expected without the package context.
    # For production, ensure it's run as part of the package.
    print("Failed to import local modules. Ensure the bot is run as a module or package.")
    print("Attempting to import assuming script is in 'bot' directory for development.")
    from config import BOT_TOKEN
    from handlers import router as main_router


async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
    
    # All handlers should be attached to the Router Pursuit
    dp = Dispatcher()
    dp.include_router(main_router) # Include the router from handlers.py

    # And the run events dispatching
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
