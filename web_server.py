"""
Веб-сервер для мини-приложения и API
"""
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import aiohttp
import asyncio
import os
from kinopoisk_api import get_popular_movies, get_popular_tv, get_movie_by_id
from database import get_favorites, add_to_favorites, is_in_favorites
import random
import logging

app = Flask(__name__, static_folder='webapp', static_url_path='')
CORS(app)

logger = logging.getLogger(__name__)

# Кэш для очереди фильмов
movies_cache = []


def run_async(coro):
    """Запустить асинхронную функцию"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route('/')
def index():
    """Главная страница мини-приложения"""
    return send_from_directory('webapp', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Отдача статических файлов"""
    return send_from_directory('webapp', path)


@app.route('/api/get_movie')
def api_get_movie():
    """Получить случайный фильм"""
    try:
        user_id = request.args.get('user_id', type=int)
        
        async def _get_movie():
            async with aiohttp.ClientSession() as session:
                # Получаем популярные фильмы
                data = await get_popular_movies(session, page=random.randint(1, 10))
                
                if data and data.get('docs'):
                    movie = random.choice(data['docs'])
                    return {'success': True, 'movie': movie}
                return {'success': False, 'message': 'Фильмы не найдены'}
        
        result = run_async(_get_movie())
        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка API get_movie: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/get_popular')
def api_get_popular():
    """Получить популярные фильмы"""
    try:
        media_type = request.args.get('type', 'movie')
        limit = request.args.get('limit', 10, type=int)
        
        async def _get_popular():
            async with aiohttp.ClientSession() as session:
                if media_type == 'movie':
                    data = await get_popular_movies(session, page=random.randint(1, 10))
                else:
                    data = await get_popular_tv(session, page=random.randint(1, 10))
                
                if data and data.get('docs'):
                    movies = data['docs'][:limit]
                    return {'success': True, 'movies': movies}
                return {'success': False, 'message': 'Фильмы не найдены'}
        
        result = run_async(_get_popular())
        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка API get_popular: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/get_favorites', methods=['GET'])
def api_get_favorites():
    """Получить избранное пользователя"""
    try:
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id required'}), 400
        
        favorites = get_favorites(user_id)
        
        return jsonify({
            'success': True,
            'favorites': favorites
        })
    except Exception as e:
        logger.error(f"Ошибка API get_favorites: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/add_favorite', methods=['POST'])
def api_add_favorite():
    """Добавить фильм в избранное"""
    try:
        data = request.json
        user_id = data.get('user_id')
        movie = data.get('movie')
        
        if not user_id or not movie:
            return jsonify({'success': False, 'message': 'user_id and movie required'}), 400
        
        if add_to_favorites(user_id, movie):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to add to favorites'}), 500
    except Exception as e:
        logger.error(f"Ошибка API add_favorite: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/check_favorite', methods=['GET'])
def api_check_favorite():
    """Проверить, есть ли фильм в избранном"""
    try:
        user_id = request.args.get('user_id', type=int)
        movie_id = request.args.get('movie_id', type=int)
        
        if not user_id or not movie_id:
            return jsonify({'success': False, 'message': 'user_id and movie_id required'}), 400
        
        is_fav = is_in_favorites(user_id, movie_id)
        
        return jsonify({
            'success': True,
            'is_favorite': is_fav
        })
    except Exception as e:
        logger.error(f"Ошибка API check_favorite: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    # Получаем порт из переменной окружения (для Render, Heroku и др.)
    # Если не установлена, используем 5000 по умолчанию
    port = int(os.environ.get('PORT', 5000))
    # Для запуска на локальной машине или на сервере
    app.run(host='0.0.0.0', port=port, debug=False)

