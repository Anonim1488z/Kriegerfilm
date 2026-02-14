import logging
import random
import aiohttp
import json
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, KINOPOISK_API_KEY
from kinopoisk_api import (
    get_popular_movies, get_popular_tv, get_top_movies, get_top_tv,
    get_movies_by_genre, search_movies, format_movie_info, GENRES, get_movie_by_id
)
from wink_api import get_wink_link, format_wink_info
from database import (
    init_database, add_to_favorites, remove_from_favorites,
    get_favorites, is_in_favorites, get_favorites_count
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Monkey patch для исправления проблемы с Updater
try:
    from telegram.ext import Updater
    
    # Сохраняем оригинальный __init__
    original_updater_init = Updater.__init__
    
    # Создаем новый __init__ без проблемного атрибута
    def patched_updater_init(self, *args, **kwargs):
        # Сначала вызываем оригинальный __init__ через object.__setattr__ чтобы избежать проблемы
        # Но мы не можем вызвать оригинал напрямую из-за ошибки
        # Поэтому используем обходной путь
        
        # Создаем атрибут через object.__setattr__ до вызова оригинального __init__
        try:
            object.__setattr__(self, '_Updater__polling_cleanup_cb', None)
        except AttributeError:
            pass
        
        # Теперь вызываем оригинальный __init__
        original_updater_init(self, *args, **kwargs)
    
    # Применяем патч
    Updater.__init__ = patched_updater_init
    logger.info("Monkey patch для Updater применен")
except Exception as e:
    logger.warning(f"Не удалось применить monkey patch: {e}")

# Жанры для отображения в боте
GENRES_DISPLAY = {
    'movie': [
        ('боевик', 'Боевик'),
        ('приключения', 'Приключения'),
        ('комедия', 'Комедия'),
        ('драма', 'Драма'),
        ('триллер', 'Триллер'),
        ('ужасы', 'Ужасы'),
        ('фантастика', 'Фантастика'),
        ('фэнтези', 'Фэнтези'),
        ('детектив', 'Детектив'),
        ('мелодрама', 'Мелодрама'),
        ('криминал', 'Криминал'),
        ('мультфильм', 'Мультфильм')
    ],
    'tv': [
        ('боевик', 'Боевик'),
        ('приключения', 'Приключения'),
        ('комедия', 'Комедия'),
        ('драма', 'Драма'),
        ('триллер', 'Триллер'),
        ('ужасы', 'Ужасы'),
        ('фантастика', 'Фантастика'),
        ('фэнтези', 'Фэнтези'),
        ('детектив', 'Детектив'),
        ('мелодрама', 'Мелодрама'),
        ('криминал', 'Криминал'),
        ('мультфильм', 'Мультфильм')
    ]
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    favorites_count = get_favorites_count(user_id)
    
    welcome_text = f"""
🎬 <b>Добро пожаловать в бота для поиска фильмов и сериалов!</b>

Я помогу вам найти что посмотреть вечером 🌙
Данные синхронизированы с <b>Кинопоиском</b> и <b>Wink</b>

💾 В избранном: {favorites_count} фильмов

Выберите, что вас интересует:
"""
    # URL для Web App (замените на ваш актуальный URL)
    web_app_url = "https://your-domain.com"  # Замените на ваш URL
    
    keyboard = [
        [InlineKeyboardButton("📱 Открыть мини-приложение", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("🎬 Популярные фильмы", callback_data='popular_movies')],
        [InlineKeyboardButton("📺 Популярные сериалы", callback_data='popular_tv')],
        [InlineKeyboardButton("⭐ Топ фильмы", callback_data='top_movies')],
        [InlineKeyboardButton("⭐ Топ сериалы", callback_data='top_tv')],
        [InlineKeyboardButton("🎭 Фильмы по жанрам", callback_data='genres_movies')],
        [InlineKeyboardButton("🎭 Сериалы по жанрам", callback_data='genres_tv')],
        [InlineKeyboardButton("🎲 Случайный фильм", callback_data='random_movie')],
        [InlineKeyboardButton("🎲 Случайный сериал", callback_data='random_tv')],
        [InlineKeyboardButton("⭐ Избранное", callback_data='favorites')],
        [InlineKeyboardButton("🔍 Поиск", callback_data='search')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def send_movie_info(message, movie_data: dict, media_type: str = 'movie', callback_data: str = None, user_id: int = None):
    """Отправить информацию о фильме/сериале"""
    if not movie_data:
        await message.reply_text(
            "❌ Не удалось получить информацию о фильме. Попробуйте еще раз.",
            parse_mode='HTML'
        )
        return
    
    text, poster_url = format_movie_info(movie_data, media_type)
    
    # Добавляем информацию о Wink
    movie_name = movie_data.get('name') or movie_data.get('alternativeName') or ''
    async with aiohttp.ClientSession() as session:
        wink_url = await get_wink_link(session, movie_name)
        if wink_url:
            wink_text = format_wink_info(movie_name, wink_url)
            text += f"\n\n{wink_text}"
    
    keyboard = []
    
    # Кнопка избранного
    if user_id:
        movie_id = movie_data.get('id')
        if movie_id and is_in_favorites(user_id, movie_id):
            keyboard.append([InlineKeyboardButton("❌ Удалить из избранного", callback_data=f'remove_fav_{movie_id}')])
        else:
            keyboard.append([InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f'add_fav_{movie_id}')])
    
    if callback_data:
        keyboard.append([InlineKeyboardButton("🔄 Еще", callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if poster_url:
            await message.reply_photo(
                photo=poster_url,
                caption=text,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
        else:
            await message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
    except Exception as e:
        logger.error(f"Error sending movie info: {e}")
        # Если не удалось отправить с фото, отправляем без фото
        await message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML',
            disable_web_page_preview=False
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    async with aiohttp.ClientSession() as session:
        if query.data == 'popular_movies':
            data = await get_popular_movies(session)
            if data and data.get('docs'):
                movie = random.choice(data['docs'][:10])
                await send_movie_info(query.message, movie, 'movie', 'popular_movies', query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось получить фильмы. Попробуйте позже.")
        
        elif query.data == 'popular_tv':
            data = await get_popular_tv(session)
            if data and data.get('docs'):
                tv = random.choice(data['docs'][:10])
                await send_movie_info(query.message, tv, 'tv', 'popular_tv', query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось получить сериалы. Попробуйте позже.")
        
        elif query.data == 'top_movies':
            data = await get_top_movies(session)
            if data and data.get('docs'):
                movie = random.choice(data['docs'][:10])
                await send_movie_info(query.message, movie, 'movie', 'top_movies', query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось получить фильмы. Попробуйте позже.")
        
        elif query.data == 'top_tv':
            data = await get_top_tv(session)
            if data and data.get('docs'):
                tv = random.choice(data['docs'][:10])
                await send_movie_info(query.message, tv, 'tv', 'top_tv', query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось получить сериалы. Попробуйте позже.")
        
        elif query.data == 'genres_movies':
            keyboard = []
            genres_list = GENRES_DISPLAY['movie']
            for i in range(0, len(genres_list), 2):
                row = []
                for j in range(2):
                    if i + j < len(genres_list):
                        genre_key, genre_name = genres_list[i + j]
                        row.append(InlineKeyboardButton(
                            genre_name,
                            callback_data=f'genre_movie_{genre_key}'
                        ))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "🎭 Выберите жанр фильма:",
                reply_markup=reply_markup
            )
        
        elif query.data == 'genres_tv':
            keyboard = []
            genres_list = GENRES_DISPLAY['tv']
            for i in range(0, len(genres_list), 2):
                row = []
                for j in range(2):
                    if i + j < len(genres_list):
                        genre_key, genre_name = genres_list[i + j]
                        row.append(InlineKeyboardButton(
                            genre_name,
                            callback_data=f'genre_tv_{genre_key}'
                        ))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "🎭 Выберите жанр сериала:",
                reply_markup=reply_markup
            )
        
        elif query.data.startswith('genre_movie_'):
            genre_key = query.data.replace('genre_movie_', '')
            data = await get_movies_by_genre(session, genre_key, type='movie')
            if data and data.get('docs'):
                movie = random.choice(data['docs'][:10])
                await send_movie_info(query.message, movie, 'movie', query.data, query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось найти фильмы этого жанра. Попробуйте позже.")
        
        elif query.data.startswith('genre_tv_'):
            genre_key = query.data.replace('genre_tv_', '')
            data = await get_movies_by_genre(session, genre_key, type='tv-series')
            if data and data.get('docs'):
                tv = random.choice(data['docs'][:10])
                await send_movie_info(query.message, tv, 'tv', query.data, query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось найти сериалы этого жанра. Попробуйте позже.")
        
        elif query.data == 'random_movie':
            page = random.randint(1, 5)
            data = await get_popular_movies(session, page)
            if data and data.get('docs'):
                movie = random.choice(data['docs'])
                await send_movie_info(query.message, movie, 'movie', 'random_movie', query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось получить фильм. Попробуйте позже.")
        
        elif query.data == 'random_tv':
            page = random.randint(1, 5)
            data = await get_popular_tv(session, page)
            if data and data.get('docs'):
                tv = random.choice(data['docs'])
                await send_movie_info(query.message, tv, 'tv', 'random_tv', query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось получить сериал. Попробуйте позже.")
        
        elif query.data == 'search':
            await query.message.reply_text(
                "🔍 <b>Поиск фильмов и сериалов</b>\n\n"
                "Отправьте название фильма или сериала, и я найду его для вас!",
                parse_mode='HTML'
            )
        
        elif query.data == 'favorites':
            user_id = query.from_user.id
            favorites = get_favorites(user_id)
            
            if not favorites:
                await query.message.reply_text(
                    "⭐ <b>Избранное пусто</b>\n\n"
                    "Добавьте фильмы в избранное, нажав кнопку '⭐ Добавить в избранное'",
                    parse_mode='HTML'
                )
            else:
                text = f"⭐ <b>Ваше избранное ({len(favorites)} фильмов)</b>\n\n"
                keyboard = []
                
                for idx, movie in enumerate(favorites[:10], 1):
                    name = movie.get('name') or movie.get('alternativeName') or 'Без названия'
                    year = movie.get('year', '')
                    movie_id = movie.get('id')
                    media_type = 'movie' if movie.get('type') == 'movie' else 'tv'
                    
                    text += f"{idx}. <b>{name}</b>"
                    if year:
                        text += f" ({year})\n"
                    else:
                        text += "\n"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"{idx}. {name}",
                        callback_data=f'view_{media_type}_{movie_id}'
                    )])
                
                keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        
        elif query.data.startswith('add_fav_'):
            movie_id = int(query.data.replace('add_fav_', ''))
            user_id = query.from_user.id
            
            async with aiohttp.ClientSession() as session:
                movie_data = await get_movie_by_id(session, movie_id)
                if movie_data:
                    if add_to_favorites(user_id, movie_data):
                        await query.answer("✅ Добавлено в избранное!", show_alert=False)
                        # Обновляем сообщение
                        media_type = 'movie' if movie_data.get('type') == 'movie' else 'tv'
                        await send_movie_info(query.message, movie_data, media_type, None, user_id)
                    else:
                        await query.answer("❌ Ошибка при добавлении", show_alert=True)
                else:
                    await query.answer("❌ Фильм не найден", show_alert=True)
        
        elif query.data.startswith('remove_fav_'):
            movie_id = int(query.data.replace('remove_fav_', ''))
            user_id = query.from_user.id
            
            if remove_from_favorites(user_id, movie_id):
                await query.answer("❌ Удалено из избранного", show_alert=False)
                # Обновляем сообщение
                async with aiohttp.ClientSession() as session:
                    movie_data = await get_movie_by_id(session, movie_id)
                    if movie_data:
                        media_type = 'movie' if movie_data.get('type') == 'movie' else 'tv'
                        await send_movie_info(query.message, movie_data, media_type, None, user_id)
            else:
                await query.answer("❌ Ошибка при удалении", show_alert=True)
        
        elif query.data == 'main_menu':
            user_id = query.from_user.id
            favorites_count = get_favorites_count(user_id)
            web_app_url = "https://your-domain.com"  # Замените на ваш URL
            
            welcome_text = f"""
🎬 <b>Главное меню</b>

💾 В избранном: {favorites_count} фильмов

Выберите, что вас интересует:
"""
            keyboard = [
                [InlineKeyboardButton("📱 Открыть мини-приложение", web_app=WebAppInfo(url=web_app_url))],
                [InlineKeyboardButton("🎬 Популярные фильмы", callback_data='popular_movies')],
                [InlineKeyboardButton("📺 Популярные сериалы", callback_data='popular_tv')],
                [InlineKeyboardButton("⭐ Топ фильмы", callback_data='top_movies')],
                [InlineKeyboardButton("⭐ Топ сериалы", callback_data='top_tv')],
                [InlineKeyboardButton("🎭 Фильмы по жанрам", callback_data='genres_movies')],
                [InlineKeyboardButton("🎭 Сериалы по жанрам", callback_data='genres_tv')],
                [InlineKeyboardButton("🎲 Случайный фильм", callback_data='random_movie')],
                [InlineKeyboardButton("🎲 Случайный сериал", callback_data='random_tv')],
                [InlineKeyboardButton("⭐ Избранное", callback_data='favorites')],
                [InlineKeyboardButton("🔍 Поиск", callback_data='search')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик поиска фильмов"""
    search_query = update.message.text.strip()
    
    if len(search_query) < 2:
        await update.message.reply_text(
            "❌ Слишком короткий запрос. Введите минимум 2 символа."
        )
        return
    
    await update.message.reply_text("🔍 Ищу...")
    
    async with aiohttp.ClientSession() as session:
        data = await search_movies(session, search_query, limit=5)
        
        if data and data.get('docs'):
            movies = data['docs'][:5]
            
            if len(movies) == 1:
                # Если найден один результат, показываем его полностью
                await send_movie_info(
                    update.message,
                    movies[0],
                    'movie' if movies[0].get('type') == 'movie' else 'tv'
                )
            else:
                # Если несколько результатов, показываем список
                text = f"🔍 <b>Найдено результатов: {len(movies)}</b>\n\n"
                keyboard = []
                
                for idx, movie in enumerate(movies, 1):
                    name = movie.get('name') or movie.get('alternativeName') or 'Без названия'
                    year = movie.get('year', '')
                    rating = movie.get('rating', {}).get('kp', 0)
                    movie_id = movie.get('id')
                    media_type = 'movie' if movie.get('type') == 'movie' else 'tv'
                    
                    text += f"{idx}. <b>{name}</b>"
                    if year:
                        text += f" ({year})"
                    if rating:
                        text += f" ⭐ {rating:.1f}\n"
                    else:
                        text += "\n"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"{idx}. {name}",
                        callback_data=f'view_{media_type}_{movie_id}'
                    )])
                
                keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                f"❌ По запросу '{search_query}' ничего не найдено. Попробуйте другой запрос."
            )


async def view_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик просмотра конкретного фильма/сериала"""
    query = update.callback_query
    await query.answer()
    
    # Формат: view_movie_123 или view_tv_123
    parts = query.data.split('_')
    if len(parts) >= 3:
        media_type = parts[1]  # movie или tv
        movie_id = int(parts[2])
        
        async with aiohttp.ClientSession() as session:
            movie_data = await get_movie_by_id(session, movie_id)
            
            if movie_data:
                await send_movie_info(query.message, movie_data, media_type, None, query.from_user.id)
            else:
                await query.message.reply_text("❌ Не удалось загрузить информацию о фильме.")


def main():
    """Главная функция для запуска бота"""
    # Инициализируем базу данных
    init_database()
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env и добавьте BOT_TOKEN")
        return
    
    if not KINOPOISK_API_KEY:
        logger.error("KINOPOISK_API_KEY не установлен! Создайте файл .env и добавьте KINOPOISK_API_KEY")
        logger.info("Получить API ключ можно на https://kinopoisk.dev/ или через @poiskkinodev_bot")
        return
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(CallbackQueryHandler(view_handler, pattern='^view_'))
        
        # Обработчик текстовых сообщений для поиска
        from telegram.ext import MessageHandler, filters
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
        
        # Запускаем бота
        logger.info("Бот запущен!")
        logger.info("Синхронизация с Кинопоиском и Wink активна!")
        logger.info("База данных избранного инициализирована!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.info("Попробуйте установить другую версию python-telegram-bot:")
        logger.info("pip uninstall python-telegram-bot")
        logger.info("pip install python-telegram-bot==20.7")


if __name__ == '__main__':
    main()
