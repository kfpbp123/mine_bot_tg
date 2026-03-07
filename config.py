import os
from dotenv import load_dotenv

load_dotenv()

# config.py (добавь эту строку, заменив 123456789 на свой реальный ID)
ADMIN_IDS = [5703605946] # Сюда можно через запятую вписать ID админов
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Получаем каналы и делаем из них список
CHANNELS_STR = os.getenv("CHANNELS", "@lazikosmods")
AVAILABLE_CHANNELS = [ch.strip() for ch in CHANNELS_STR.split(',')]
DEFAULT_CHANNEL = AVAILABLE_CHANNELS[0] if AVAILABLE_CHANNELS else ""

WATERMARK_TEXT = "@lazikosmods"