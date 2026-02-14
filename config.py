import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Кинопоиск API (kinopoisk.dev)
KINOPOISK_API_KEY = os.getenv('KINOPOISK_API_KEY', '')
KINOPOISK_BASE_URL = 'https://api.kinopoisk.dev/v1.4'
KINOPOISK_IMAGE_BASE_URL = 'https://kinopoiskapiunofficial.tech/images/posters/kp'

# Wink (для поиска фильмов)
WINK_SEARCH_URL = 'https://wink.rt.ru'

