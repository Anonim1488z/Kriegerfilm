"""
Модуль для работы с Wink (поиск фильмов на стриминговом сервисе)
"""
import logging
import aiohttp
from typing import Optional, Dict
from config import WINK_SEARCH_URL
import urllib.parse

logger = logging.getLogger(__name__)


async def search_wink(session: aiohttp.ClientSession, query: str) -> Optional[str]:
    """
    Поиск фильма/сериала на Wink
    Возвращает URL для поиска на Wink
    """
    try:
        # Кодируем запрос для URL
        encoded_query = urllib.parse.quote(query)
        wink_search_url = f"{WINK_SEARCH_URL}/search?q={encoded_query}"
        return wink_search_url
    except Exception as e:
        logger.error(f"Error creating Wink search URL: {e}")
        return None


async def get_wink_link(session: aiohttp.ClientSession, movie_name: str) -> Optional[str]:
    """
    Получить ссылку на поиск фильма на Wink
    """
    return await search_wink(session, movie_name)


def format_wink_info(movie_name: str, wink_url: Optional[str]) -> str:
    """Форматировать информацию о доступности на Wink"""
    if wink_url:
        return f"📺 <b>Доступно на Wink:</b>\n<a href='{wink_url}'>🔍 Найти на Wink</a>"
    return ""


