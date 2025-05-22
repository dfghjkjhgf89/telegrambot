import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL") # e.g., postgresql://user:password@host:port/dbname

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN environment variable not set.")
# Add more configurations as needed
