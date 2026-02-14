"""
Модуль для работы с Кинопоиск API (kinopoisk.dev)
"""
import logging
import aiohttp
from typing import Optional, Dict, List
from config import KINOPOISK_API_KEY, KINOPOISK_BASE_URL

logger = logging.getLogger(__name__)

# Жанры для фильмов
GENRES = {
    'movie': {
        'боевик': 'action',
        'приключения': 'adventure',
        'мультфильм': 'animation',
        'комедия': 'comedy',
        'криминал': 'crime',
        'документальный': 'documentary',
        'драма': 'drama',
        'семейный': 'family',
        'фэнтези': 'fantasy',
        'история': 'history',
        'ужасы': 'horror',
        'музыка': 'music',
        'детектив': 'mystery',
        'мелодрама': 'romance',
        'фантастика': 'sci-fi',
        'триллер': 'thriller',
        'военный': 'war',
        'вестерн': 'western'
    }
}


async def get_movie_by_id(session: aiohttp.ClientSession, movie_id: int) -> Optional[Dict]:
    """Получить информацию о фильме по ID"""
    url = f"{KINOPOISK_BASE_URL}/movie/{movie_id}"
    headers = {
        'X-API-KEY': KINOPOISK_API_KEY
    }
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Error fetching movie {movie_id}: {response.status}")
    except Exception as e:
        logger.error(f"Exception fetching movie {movie_id}: {e}")
    return None


async def get_movies(session: aiohttp.ClientSession, 
                     page: int = 1, 
                     limit: int = 20,
                     genre: Optional[str] = None,
                     rating_kp: Optional[float] = None,
                     year: Optional[int] = None,
                     type: str = 'movie') -> Optional[Dict]:
    """Получить список фильмов/сериалов"""
    url = f"{KINOPOISK_BASE_URL}/{type}"
    headers = {
        'X-API-KEY': KINOPOISK_API_KEY
    }
    params = {
        'page': page,
        'limit': limit,
        'sortField': 'rating.kp',
        'sortType': '-1'
    }
    
    if genre:
        params['genres.name'] = genre
    if rating_kp:
        params['rating.kp'] = f'{rating_kp}-10'
    if year:
        params['year'] = year
    
    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Error fetching movies: {response.status}")
    except Exception as e:
        logger.error(f"Exception fetching movies: {e}")
    return None


async def get_popular_movies(session: aiohttp.ClientSession, page: int = 1) -> Optional[Dict]:
    """Получить популярные фильмы"""
    return await get_movies(session, page=page, limit=20, type='movie')


async def get_popular_tv(session: aiohttp.ClientSession, page: int = 1) -> Optional[Dict]:
    """Получить популярные сериалы"""
    return await get_movies(session, page=page, limit=20, type='tv-series')


async def get_top_movies(session: aiohttp.ClientSession, page: int = 1) -> Optional[Dict]:
    """Получить топ фильмы (с высоким рейтингом)"""
    return await get_movies(session, page=page, limit=20, rating_kp=7.5, type='movie')


async def get_top_tv(session: aiohttp.ClientSession, page: int = 1) -> Optional[Dict]:
    """Получить топ сериалы (с высоким рейтингом)"""
    return await get_movies(session, page=page, limit=20, rating_kp=7.5, type='tv-series')


async def get_movies_by_genre(session: aiohttp.ClientSession, 
                              genre: str, 
                              page: int = 1,
                              type: str = 'movie') -> Optional[Dict]:
    """Получить фильмы/сериалы по жанру"""
    return await get_movies(session, page=page, limit=20, genre=genre, type=type)


async def search_movies(session: aiohttp.ClientSession, 
                       query: str, 
                       page: int = 1,
                       limit: int = 20) -> Optional[Dict]:
    """Поиск фильмов и сериалов"""
    url = f"{KINOPOISK_BASE_URL}/movie/search"
    headers = {
        'X-API-KEY': KINOPOISK_API_KEY
    }
    params = {
        'page': page,
        'limit': limit,
        'query': query
    }
    
    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Error searching movies: {response.status}")
    except Exception as e:
        logger.error(f"Exception searching movies: {e}")
    return None


def format_movie_info(data: Dict, media_type: str = 'movie') -> tuple:
    """Форматировать информацию о фильме/сериале для отправки"""
    name = data.get('name') or data.get('alternativeName') or 'Без названия'
    description = data.get('description') or data.get('shortDescription') or 'Описание отсутствует'
    rating_kp = data.get('rating', {}).get('kp', 0)
    year = data.get('year', 0)
    genres = data.get('genres', [])
    poster = data.get('poster', {})
    poster_url = poster.get('url') if poster else None
    
    # Дополнительная информация
    movie_length = data.get('movieLength')  # для фильмов
    series_length = data.get('seriesLength')  # для сериалов
    age_rating = data.get('ageRating')
    countries = data.get('countries', [])
    
    # Формируем текст
    text = f"🎬 <b>{name}</b>\n\n"
    
    if rating_kp:
        stars = '⭐' * min(int(rating_kp), 10)
        text += f"{stars} <b>{rating_kp:.1f}/10</b> (Кинопоиск)\n\n"
    
    if year:
        text += f"📅 Год: {year}\n"
    
    if genres:
        genre_names = ', '.join([g.get('name', '') for g in genres[:3] if g.get('name')])
        if genre_names:
            text += f"🎭 Жанры: {genre_names}\n"
    
    if countries:
        country_names = ', '.join([c.get('name', '') for c in countries[:2] if c.get('name')])
        if country_names:
            text += f"🌍 Страна: {country_names}\n"
    
    if age_rating:
        text += f"🔞 Возраст: {age_rating}+\n"
    
    if movie_length:
        hours = movie_length // 60
        minutes = movie_length % 60
        text += f"⏱ Длительность: {hours}ч {minutes}м\n"
    elif series_length:
        text += f"📺 Серий: {series_length}\n"
    
    text += f"\n📖 <i>{description}</i>"
    
    # Добавляем ссылку на Кинопоиск
    kp_id = data.get('id')
    if kp_id:
        text += f"\n\n🔗 <a href='https://www.kinopoisk.ru/film/{kp_id}'>Открыть на Кинопоиске</a>"
    
    return text, poster_url


