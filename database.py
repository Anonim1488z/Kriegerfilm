"""
Модуль для работы с базой данных избранных фильмов
"""
import sqlite3
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DB_NAME = 'favorites.db'


def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            movie_name TEXT NOT NULL,
            movie_type TEXT NOT NULL,
            movie_data TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, movie_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")


def add_to_favorites(user_id: int, movie_data: Dict) -> bool:
    """Добавить фильм в избранное"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        movie_id = movie_data.get('id')
        movie_name = movie_data.get('name') or movie_data.get('alternativeName') or 'Без названия'
        movie_type = movie_data.get('type', 'movie')
        
        import json
        movie_data_json = json.dumps(movie_data, ensure_ascii=False)
        
        cursor.execute('''
            INSERT OR REPLACE INTO favorites 
            (user_id, movie_id, movie_name, movie_type, movie_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, movie_id, movie_name, movie_type, movie_data_json))
        
        conn.commit()
        conn.close()
        logger.info(f"Фильм {movie_id} добавлен в избранное пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении в избранное: {e}")
        return False


def remove_from_favorites(user_id: int, movie_id: int) -> bool:
    """Удалить фильм из избранного"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM favorites 
            WHERE user_id = ? AND movie_id = ?
        ''', (user_id, movie_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Фильм {movie_id} удален из избранного пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении из избранного: {e}")
        return False


def get_favorites(user_id: int, limit: int = 50) -> List[Dict]:
    """Получить список избранных фильмов пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT movie_data FROM favorites 
            WHERE user_id = ? 
            ORDER BY added_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        import json
        favorites = []
        for row in results:
            try:
                movie_data = json.loads(row[0])
                favorites.append(movie_data)
            except:
                pass
        
        return favorites
    except Exception as e:
        logger.error(f"Ошибка при получении избранного: {e}")
        return []


def is_in_favorites(user_id: int, movie_id: int) -> bool:
    """Проверить, есть ли фильм в избранном"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM favorites 
            WHERE user_id = ? AND movie_id = ?
        ''', (user_id, movie_id))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    except Exception as e:
        logger.error(f"Ошибка при проверке избранного: {e}")
        return False


def get_favorites_count(user_id: int) -> int:
    """Получить количество избранных фильмов"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM favorites 
            WHERE user_id = ?
        ''', (user_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    except Exception as e:
        logger.error(f"Ошибка при подсчете избранного: {e}")
        return 0


