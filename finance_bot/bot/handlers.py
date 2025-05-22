from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(f"Hello, {message.from_user.full_name}! Welcome to FinanceBot. I'm here to help you manage shared expenses.")
    # Here you would typically add the user to the database if they are new.
    # For now, just a welcome message.

# Add more handlers here as functionality is built
