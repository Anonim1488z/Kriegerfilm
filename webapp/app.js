// Инициализация Telegram Web App
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// API URL (замените на ваш домен)
const API_URL = 'https://service-production-25ac.up.railway.app/api';  // Замените на ваш URL

// Состояние приложения
let currentMovie = null;
let viewedCount = 0;
let favoritesCount = 0;
let currentIndex = 0;
let moviesQueue = [];

// Элементы DOM
const movieCard = document.getElementById('movieCard');
const movieContent = document.getElementById('movieContent');
const loading = document.getElementById('loading');
const poster = document.getElementById('poster');
const title = document.getElementById('title');
const rating = document.getElementById('rating');
const details = document.getElementById('details');
const description = document.getElementById('description');
const likeBtn = document.getElementById('likeBtn');
const dislikeBtn = document.getElementById('dislikeBtn');
const viewedCountEl = document.getElementById('viewedCount');
const favoritesCountEl = document.getElementById('favoritesCount');
const favoritesBtn = document.getElementById('favoritesBtn');
const refreshBtn = document.getElementById('refreshBtn');
const favoritesModal = document.getElementById('favoritesModal');
const favoritesList = document.getElementById('favoritesList');
const closeModal = document.getElementById('closeModal');

// Получить user_id из Telegram
const userId = tg.initDataUnsafe?.user?.id || tg.initDataUnsafe?.user?.id;

// Инициализация свайпов
let startX = 0;
let startY = 0;
let currentX = 0;
let currentY = 0;
let isDragging = false;

// Создать индикатор свайпа
const swipeIndicator = document.createElement('div');
swipeIndicator.className = 'swipe-indicator';
movieCard.appendChild(swipeIndicator);

// Загрузка фильма
async function loadMovie() {
    try {
        loading.style.display = 'block';
        movieContent.style.display = 'none';
        
        // Если очередь пуста, загружаем новые фильмы
        if (moviesQueue.length === 0) {
            const response = await fetch(`${API_URL}/get_movie?user_id=${userId}`);
            const data = await response.json();
            
            if (data.success && data.movie) {
                moviesQueue.push(data.movie);
            } else {
                // Загружаем популярные фильмы
                const popularResponse = await fetch(`${API_URL}/get_popular?type=movie&limit=10`);
                const popularData = await popularResponse.json();
                if (popularData.success && popularData.movies) {
                    moviesQueue = popularData.movies;
                }
            }
        }
        
        if (moviesQueue.length > 0) {
            currentMovie = moviesQueue.shift();
            displayMovie(currentMovie);
            viewedCount++;
            updateStats();
        } else {
            loading.textContent = 'Фильмы закончились. Нажмите "Обновить"';
        }
    } catch (error) {
        console.error('Ошибка загрузки фильма:', error);
        loading.textContent = 'Ошибка загрузки. Попробуйте еще раз.';
    }
}

// Отображение фильма
function displayMovie(movie) {
    loading.style.display = 'none';
    movieContent.style.display = 'block';
    
    const name = movie.name || movie.alternativeName || 'Без названия';
    const year = movie.year || '';
    const ratingKp = movie.rating?.kp || 0;
    const genres = (movie.genres || []).map(g => g.name).join(', ');
    const countries = (movie.countries || []).map(c => c.name).join(', ');
    const desc = movie.description || movie.shortDescription || 'Описание отсутствует';
    const posterUrl = movie.poster?.url || movie.poster?.previewUrl || '';
    
    title.textContent = name;
    rating.textContent = ratingKp > 0 ? '⭐ '.repeat(Math.min(Math.floor(ratingKp), 5)) + ` ${ratingKp.toFixed(1)}/10` : '';
    
    let detailsText = '';
    if (year) detailsText += `📅 ${year} `;
    if (genres) detailsText += `\n🎭 ${genres} `;
    if (countries) detailsText += `\n🌍 ${countries}`;
    details.textContent = detailsText;
    
    description.textContent = desc;
    
    if (posterUrl) {
        poster.src = posterUrl;
        poster.onerror = function() {
            this.src = 'https://via.placeholder.com/400x600?text=No+Poster';
        };
    } else {
        poster.src = 'https://via.placeholder.com/400x600?text=No+Poster';
    }
    
    currentMovie = movie;
}

// Добавить в избранное
async function addToFavorites() {
    if (!currentMovie) return;
    
    try {
        const response = await fetch(`${API_URL}/add_favorite`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                movie: currentMovie
            })
        });
        
        const data = await response.json();
        if (data.success) {
            favoritesCount++;
            updateStats();
            tg.showAlert('✅ Добавлено в избранное!');
        }
    } catch (error) {
        console.error('Ошибка добавления в избранное:', error);
    }
    
    loadMovie();
}

// Пропустить фильм
function skipMovie() {
    loadMovie();
}

// Обновить статистику
function updateStats() {
    viewedCountEl.textContent = viewedCount;
    favoritesCountEl.textContent = favoritesCount;
}

// Загрузить избранное
async function loadFavorites() {
    try {
        const response = await fetch(`${API_URL}/get_favorites?user_id=${userId}`);
        const data = await response.json();
        
        if (data.success && data.favorites) {
            favoritesList.innerHTML = '';
            
            if (data.favorites.length === 0) {
                favoritesList.innerHTML = '<div style="padding: 20px; text-align: center; color: #6b7280;">Избранное пусто</div>';
            } else {
                data.favorites.forEach(movie => {
                    const item = document.createElement('div');
                    item.className = 'favorite-item';
                    const name = movie.name || movie.alternativeName || 'Без названия';
                    const year = movie.year || '';
                    item.innerHTML = `
                        <h3>${name}</h3>
                        ${year ? `<div class="year">${year}</div>` : ''}
                    `;
                    item.onclick = () => {
                        displayMovie(movie);
                        favoritesModal.style.display = 'none';
                    };
                    favoritesList.appendChild(item);
                });
            }
            
            favoritesModal.style.display = 'flex';
        }
    } catch (error) {
        console.error('Ошибка загрузки избранного:', error);
        tg.showAlert('Ошибка загрузки избранного');
    }
}

// Свайп обработчики
movieCard.addEventListener('touchstart', (e) => {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    isDragging = true;
    movieCard.style.transition = 'none';
});

movieCard.addEventListener('touchmove', (e) => {
    if (!isDragging) return;
    
    currentX = e.touches[0].clientX - startX;
    currentY = e.touches[0].clientY - startY;
    
    const rotation = currentX * 0.1;
    movieCard.style.transform = `translateX(${currentX}px) rotate(${rotation}deg)`;
    
    // Показываем индикатор
    if (Math.abs(currentX) > 50) {
        swipeIndicator.style.opacity = '0.8';
        if (currentX > 0) {
            swipeIndicator.textContent = '👍';
            swipeIndicator.className = 'swipe-indicator show like';
            movieCard.classList.add('swiping-right');
            movieCard.classList.remove('swiping-left');
        } else {
            swipeIndicator.textContent = '👎';
            swipeIndicator.className = 'swipe-indicator show dislike';
            movieCard.classList.add('swiping-left');
            movieCard.classList.remove('swiping-right');
        }
    } else {
        swipeIndicator.style.opacity = '0';
        movieCard.classList.remove('swiping-right', 'swiping-left');
    }
});

movieCard.addEventListener('touchend', () => {
    if (!isDragging) return;
    isDragging = false;
    
    movieCard.style.transition = 'transform 0.3s ease';
    swipeIndicator.style.opacity = '0';
    
    if (Math.abs(currentX) > 100) {
        if (currentX > 0) {
            // Свайп вправо - в избранное
            addToFavorites();
        } else {
            // Свайп влево - пропустить
            skipMovie();
        }
    }
    
    movieCard.style.transform = '';
    movieCard.classList.remove('swiping-right', 'swiping-left');
    currentX = 0;
    currentY = 0;
});

// Кнопки
likeBtn.addEventListener('click', addToFavorites);
dislikeBtn.addEventListener('click', skipMovie);
favoritesBtn.addEventListener('click', loadFavorites);
refreshBtn.addEventListener('click', () => {
    moviesQueue = [];
    loadMovie();
});
closeModal.addEventListener('click', () => {
    favoritesModal.style.display = 'none';
});

// Инициализация
loadMovie();
updateStats();


