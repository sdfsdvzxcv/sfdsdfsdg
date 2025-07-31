// Глобальные переменные
let currentUser = null;
let isAdmin = false;
let poems = [];
let authors = [];
let currentPage = 1;
let searchQuery = '';
let currentFilter = 'all';

// API endpoints
const API_BASE = 'http://localhost:5000/api';

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadInitialData();
});

// Инициализация приложения
function initializeApp() {
    // Проверяем авторизацию
    checkAuth();
    
    // Настройка мобильного меню
    setupMobileMenu();
    
    // Настройка плавной прокрутки
    setupSmoothScrolling();
    
    // Настройка модальных окон
    setupModals();
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Поиск стихов
    const searchInput = document.getElementById('poemSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(searchPoems, 300));
    }
    
    // Фильтры
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            filterPoems();
        });
    });
    
    // Админ панель
    const adminMenuItems = document.querySelectorAll('.admin-menu-item[data-panel]');
    adminMenuItems.forEach(item => {
        item.addEventListener('click', () => {
            switchAdminPanel(item.dataset.panel);
        });
    });
    
    // Формы
    setupForms();
}

// Настройка мобильного меню
function setupMobileMenu() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });
    }
}

// Настройка плавной прокрутки
function setupSmoothScrolling() {
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth' });
                // Обновляем активную ссылку
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            }
        });
    });
}

// Настройка модальных окон
function setupModals() {
    const modals = document.querySelectorAll('.modal');
    const closeButtons = document.querySelectorAll('.close');
    
    // Закрытие по клику на крестик
    closeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    // Закрытие по клику вне модального окна
    modals.forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// Настройка форм
function setupForms() {
    // Форма добавления стихотворения
    const addPoemForm = document.getElementById('addPoemForm');
    if (addPoemForm) {
        addPoemForm.addEventListener('submit', handleAddPoem);
    }
    
    // Форма добавления автора
    const addAuthorForm = document.getElementById('addAuthorForm');
    if (addAuthorForm) {
        addAuthorForm.addEventListener('submit', handleAddAuthor);
    }
}

// Загрузка начальных данных
async function loadInitialData() {
    showLoader();
    try {
        await Promise.all([
            loadPoems(),
            loadAuthors(),
            loadStats()
        ]);
    } catch (error) {
        console.error('Error loading initial data:', error);
        showNotification('Ошибка загрузки данных', 'error');
    } finally {
        hideLoader();
    }
}

// API функции
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options
    };
    
    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Загрузка стихов
async function loadPoems() {
    try {
        const data = await apiRequest('/poems');
        poems = data.poems || [];
        renderPoems();
    } catch (error) {
        console.error('Error loading poems:', error);
    }
}

// Загрузка авторов
async function loadAuthors() {
    try {
        const data = await apiRequest('/authors');
        authors = data.authors || [];
        renderAuthors();
        populateAuthorSelects();
    } catch (error) {
        console.error('Error loading authors:', error);
    }
}

// Загрузка статистики
async function loadStats() {
    try {
        const data = await apiRequest('/stats');
        updateStats(data);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Рендеринг стихов
function renderPoems() {
    const poemsGrid = document.getElementById('poemsGrid');
    if (!poemsGrid) return;
    
    const filteredPoems = filterPoemsBySearch(poems);
    
    poemsGrid.innerHTML = filteredPoems.map(poem => `
        <div class="poem-card" onclick="showPoemModal(${poem.id})">
            <div class="poem-title">${poem.title}</div>
            <div class="poem-author">${poem.author_name || 'Неизвестный автор'}</div>
            <div class="poem-preview">${poem.preview || poem.content.substring(0, 150)}...</div>
            <div class="poem-actions">
                <button class="poem-action-btn save" onclick="event.stopPropagation(); savePoemToLibrary(${poem.id})">
                    <i class="fas fa-bookmark"></i> Сохранить
                </button>
                <button class="poem-action-btn share" onclick="event.stopPropagation(); sharePoem(${poem.id})">
                    <i class="fas fa-share"></i> Поделиться
                </button>
            </div>
        </div>
    `).join('');
}

// Рендеринг авторов
function renderAuthors() {
    const authorsGrid = document.getElementById('authorsGrid');
    if (!authorsGrid) return;
    
    authorsGrid.innerHTML = authors.map(author => `
        <div class="author-card" onclick="showAuthorPoems(${author.id})">
            <div class="author-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="author-name">${author.name}</div>
            <div class="author-info">
                ${author.country ? `${author.country}` : ''}
                ${author.period ? ` • ${author.period}` : ''}
            </div>
        </div>
    `).join('');
}

// Заполнение селектов авторов
function populateAuthorSelects() {
    const authorSelects = document.querySelectorAll('#poemAuthor, #libraryAuthorFilter');
    authorSelects.forEach(select => {
        select.innerHTML = '<option value="">Выберите автора</option>' +
            authors.map(author => `<option value="${author.id}">${author.name}</option>`).join('');
    });
}

// Обновление статистики
function updateStats(stats) {
    document.getElementById('totalUsers').textContent = stats.total_users || 0;
    document.getElementById('totalPoems').textContent = stats.total_poems || 0;
    document.getElementById('totalAuthors').textContent = stats.total_authors || 0;
    document.getElementById('pendingSubmissions').textContent = stats.pending_submissions || 0;
}

// Поиск стихов
function searchPoems() {
    const searchInput = document.getElementById('poemSearch');
    if (searchInput) {
        searchQuery = searchInput.value.toLowerCase();
        filterPoems();
    }
}

// Фильтрация стихов
function filterPoems() {
    let filteredPoems = poems;
    
    // Поиск
    if (searchQuery) {
        filteredPoems = filteredPoems.filter(poem => 
            poem.title.toLowerCase().includes(searchQuery) ||
            (poem.author_name && poem.author_name.toLowerCase().includes(searchQuery)) ||
            (poem.genre && poem.genre.toLowerCase().includes(searchQuery))
        );
    }
    
    // Фильтр по типу
    switch (currentFilter) {
        case 'author':
            // Показать только стихи с авторами
            filteredPoems = filteredPoems.filter(poem => poem.author_id);
            break;
        case 'genre':
            // Показать только стихи с жанрами
            filteredPoems = filteredPoems.filter(poem => poem.genre);
            break;
        case 'period':
            // Показать только стихи с периодами
            filteredPoems = filteredPoems.filter(poem => poem.period);
            break;
    }
    
    renderFilteredPoems(filteredPoems);
}

// Рендеринг отфильтрованных стихов
function renderFilteredPoems(filteredPoems) {
    const poemsGrid = document.getElementById('poemsGrid');
    if (!poemsGrid) return;
    
    poemsGrid.innerHTML = filteredPoems.map(poem => `
        <div class="poem-card" onclick="showPoemModal(${poem.id})">
            <div class="poem-title">${poem.title}</div>
            <div class="poem-author">${poem.author_name || 'Неизвестный автор'}</div>
            <div class="poem-preview">${poem.preview || poem.content.substring(0, 150)}...</div>
            <div class="poem-actions">
                <button class="poem-action-btn save" onclick="event.stopPropagation(); savePoemToLibrary(${poem.id})">
                    <i class="fas fa-bookmark"></i> Сохранить
                </button>
                <button class="poem-action-btn share" onclick="event.stopPropagation(); sharePoem(${poem.id})">
                    <i class="fas fa-share"></i> Поделиться
                </button>
            </div>
        </div>
    `).join('');
}

// Фильтрация стихов по поиску
function filterPoemsBySearch(poems) {
    if (!searchQuery) return poems;
    
    return poems.filter(poem => 
        poem.title.toLowerCase().includes(searchQuery) ||
        (poem.author_name && poem.author_name.toLowerCase().includes(searchQuery)) ||
        (poem.genre && poem.genre.toLowerCase().includes(searchQuery))
    );
}

// Получение случайного стихотворения
async function getRandomPoem() {
    showLoader();
    try {
        const data = await apiRequest('/poems/random');
        if (data.poem) {
            showPoemModal(data.poem.id);
        }
    } catch (error) {
        console.error('Error getting random poem:', error);
        showNotification('Ошибка получения случайного стихотворения', 'error');
    } finally {
        hideLoader();
    }
}

// Показать модальное окно стихотворения
async function showPoemModal(poemId) {
    try {
        const data = await apiRequest(`/poems/${poemId}`);
        const poem = data.poem;
        
        const modal = document.getElementById('poemModal');
        const content = document.getElementById('poemModalContent');
        
        content.innerHTML = `
            <h2>${poem.title}</h2>
            <p class="poem-author-modal">${poem.author_name || 'Неизвестный автор'}</p>
            <div class="poem-content">
                ${formatPoemContent(poem.content)}
            </div>
            <div class="poem-actions-modal">
                <button class="btn btn-primary" onclick="savePoemToLibrary(${poem.id})">
                    <i class="fas fa-bookmark"></i> Сохранить в библиотеку
                </button>
                <button class="btn btn-secondary" onclick="sharePoem(${poem.id})">
                    <i class="fas fa-share"></i> Поделиться
                </button>
            </div>
        `;
        
        modal.style.display = 'block';
    } catch (error) {
        console.error('Error showing poem modal:', error);
        showNotification('Ошибка загрузки стихотворения', 'error');
    }
}

// Форматирование содержимого стихотворения
function formatPoemContent(content) {
    // Разбиваем на строки и добавляем выделение цитат
    const lines = content.split('\n');
    return lines.map(line => {
        // Выделяем цитаты (текст в кавычках)
        const formattedLine = line.replace(/"([^"]+)"/g, '<span class="quote">"$1"</span>');
        return `<p>${formattedLine}</p>`;
    }).join('');
}

// Сохранение стихотворения в библиотеку
async function savePoemToLibrary(poemId) {
    if (!currentUser) {
        showNotification('Необходимо войти в систему', 'warning');
        return;
    }
    
    try {
        await apiRequest('/library/save', {
            method: 'POST',
            body: JSON.stringify({ poem_id: poemId })
        });
        
        showNotification('Стихотворение добавлено в библиотеку', 'success');
        updateLibraryCount();
    } catch (error) {
        console.error('Error saving poem to library:', error);
        showNotification('Ошибка сохранения стихотворения', 'error');
    }
}

// Поделиться стихотворением
async function sharePoem(poemId) {
    try {
        const data = await apiRequest(`/poems/${poemId}`);
        const poem = data.poem;
        
        const shareText = `${poem.title}\n\n${poem.author_name || 'Неизвестный автор'}\n\n${poem.content}\n\nПоделено через Рильке`;
        
        if (navigator.share) {
            await navigator.share({
                title: poem.title,
                text: shareText,
                url: window.location.href
            });
        } else {
            // Fallback для браузеров без Web Share API
            await navigator.clipboard.writeText(shareText);
            showNotification('Стихотворение скопировано в буфер обмена', 'success');
        }
    } catch (error) {
        console.error('Error sharing poem:', error);
        showNotification('Ошибка при попытке поделиться', 'error');
    }
}

// Показать стихи автора
async function showAuthorPoems(authorId) {
    try {
        const data = await apiRequest(`/authors/${authorId}/poems`);
        const authorPoems = data.poems || [];
        
        // Обновляем сетку стихов
        const poemsGrid = document.getElementById('poemsGrid');
        if (poemsGrid) {
            poemsGrid.innerHTML = authorPoems.map(poem => `
                <div class="poem-card" onclick="showPoemModal(${poem.id})">
                    <div class="poem-title">${poem.title}</div>
                    <div class="poem-preview">${poem.preview || poem.content.substring(0, 150)}...</div>
                    <div class="poem-actions">
                        <button class="poem-action-btn save" onclick="event.stopPropagation(); savePoemToLibrary(${poem.id})">
                            <i class="fas fa-bookmark"></i> Сохранить
                        </button>
                        <button class="poem-action-btn share" onclick="event.stopPropagation(); sharePoem(${poem.id})">
                            <i class="fas fa-share"></i> Поделиться
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        // Прокручиваем к секции стихов
        scrollToSection('poems');
    } catch (error) {
        console.error('Error showing author poems:', error);
        showNotification('Ошибка загрузки стихов автора', 'error');
    }
}

// Админ функции
function adminLogin() {
    const username = document.getElementById('adminUsername').value;
    const password = document.getElementById('adminPassword').value;
    
    if (!username || !password) {
        showNotification('Введите имя пользователя и пароль', 'warning');
        return;
    }
    
    // Простая проверка (в реальном проекте должна быть серверная аутентификация)
    if (username === 'admin' && password === 'admin123') {
        isAdmin = true;
        document.getElementById('adminLogin').style.display = 'none';
        document.getElementById('adminPanel').style.display = 'block';
        loadAdminData();
        showNotification('Вход выполнен успешно', 'success');
    } else {
        showNotification('Неверные учетные данные', 'error');
    }
}

function adminLogout() {
    isAdmin = false;
    document.getElementById('adminLogin').style.display = 'block';
    document.getElementById('adminPanel').style.display = 'none';
    document.getElementById('adminUsername').value = '';
    document.getElementById('adminPassword').value = '';
    showNotification('Выход выполнен', 'info');
}

// Переключение панелей админа
function switchAdminPanel(panelName) {
    // Скрываем все панели
    const panels = document.querySelectorAll('.admin-panel-content');
    panels.forEach(panel => panel.classList.remove('active'));
    
    // Показываем нужную панель
    const targetPanel = document.getElementById(`${panelName}Panel`);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }
    
    // Обновляем активную кнопку меню
    const menuItems = document.querySelectorAll('.admin-menu-item');
    menuItems.forEach(item => item.classList.remove('active'));
    event.target.classList.add('active');
}

// Загрузка данных для админ панели
async function loadAdminData() {
    try {
        await Promise.all([
            loadAdminPoems(),
            loadAdminAuthors(),
            loadAdminSubmissions()
        ]);
    } catch (error) {
        console.error('Error loading admin data:', error);
    }
}

// Загрузка стихов для админ панели
async function loadAdminPoems() {
    try {
        const data = await apiRequest('/admin/poems');
        const adminPoems = data.poems || [];
        
        const tbody = document.getElementById('poemsTableBody');
        if (tbody) {
            tbody.innerHTML = adminPoems.map(poem => `
                <tr>
                    <td>${poem.title}</td>
                    <td>${poem.author_name || 'Неизвестный автор'}</td>
                    <td>${poem.genre || '-'}</td>
                    <td>${new Date(poem.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-secondary" onclick="editPoem(${poem.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline" onclick="deletePoem(${poem.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading admin poems:', error);
    }
}

// Загрузка авторов для админ панели
async function loadAdminAuthors() {
    try {
        const data = await apiRequest('/admin/authors');
        const adminAuthors = data.authors || [];
        
        const tbody = document.getElementById('authorsTableBody');
        if (tbody) {
            tbody.innerHTML = adminAuthors.map(author => `
                <tr>
                    <td>${author.name}</td>
                    <td>${author.country || '-'}</td>
                    <td>${author.period || '-'}</td>
                    <td>${author.poems_count || 0}</td>
                    <td>
                        <button class="btn btn-secondary" onclick="editAuthor(${author.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline" onclick="deleteAuthor(${author.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading admin authors:', error);
    }
}

// Загрузка предложений для админ панели
async function loadAdminSubmissions() {
    try {
        const data = await apiRequest('/admin/submissions');
        const submissions = data.submissions || [];
        
        const submissionsList = document.getElementById('submissionsList');
        if (submissionsList) {
            submissionsList.innerHTML = submissions.map(submission => `
                <div class="submission-item">
                    <div class="submission-header">
                        <span class="submission-user">${submission.user_name || 'Пользователь'}</span>
                        <span class="submission-date">${new Date(submission.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="submission-content">${submission.content}</div>
                    <div class="submission-actions">
                        <button class="btn btn-primary" onclick="approveSubmission(${submission.id})">
                            <i class="fas fa-check"></i> Одобрить
                        </button>
                        <button class="btn btn-outline" onclick="rejectSubmission(${submission.id})">
                            <i class="fas fa-times"></i> Отклонить
                        </button>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading admin submissions:', error);
    }
}

// Показать форму добавления стихотворения
function showAddPoemForm() {
    const modal = document.getElementById('addPoemModal');
    modal.style.display = 'block';
}

// Показать форму добавления автора
function showAddAuthorForm() {
    const modal = document.getElementById('addAuthorModal');
    modal.style.display = 'block';
}

// Обработка добавления стихотворения
async function handleAddPoem(event) {
    event.preventDefault();
    
    const formData = {
        title: document.getElementById('poemTitle').value,
        author_id: document.getElementById('poemAuthor').value,
        genre: document.getElementById('poemGenre').value,
        preview: document.getElementById('poemPreview').value,
        content: document.getElementById('poemContent').value
    };
    
    try {
        await apiRequest('/admin/poems', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showNotification('Стихотворение добавлено успешно', 'success');
        document.getElementById('addPoemModal').style.display = 'none';
        event.target.reset();
        loadAdminPoems();
        loadPoems();
    } catch (error) {
        console.error('Error adding poem:', error);
        showNotification('Ошибка добавления стихотворения', 'error');
    }
}

// Обработка добавления автора
async function handleAddAuthor(event) {
    event.preventDefault();
    
    const formData = {
        name: document.getElementById('authorName').value,
        country: document.getElementById('authorCountry').value,
        period: document.getElementById('authorPeriod').value
    };
    
    try {
        await apiRequest('/admin/authors', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showNotification('Автор добавлен успешно', 'success');
        document.getElementById('addAuthorModal').style.display = 'none';
        event.target.reset();
        loadAdminAuthors();
        loadAuthors();
    } catch (error) {
        console.error('Error adding author:', error);
        showNotification('Ошибка добавления автора', 'error');
    }
}

// Отправка рассылки
async function sendBroadcast() {
    const type = document.getElementById('broadcastType').value;
    const text = document.getElementById('broadcastText').value;
    const mediaFile = document.getElementById('broadcastMedia').files[0];
    
    if (!text.trim()) {
        showNotification('Введите текст сообщения', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('type', type);
    formData.append('text', text);
    if (mediaFile) {
        formData.append('media', mediaFile);
    }
    
    try {
        await fetch(`${API_BASE}/admin/broadcast`, {
            method: 'POST',
            body: formData
        });
        
        showNotification('Рассылка отправлена успешно', 'success');
        document.getElementById('broadcastText').value = '';
        document.getElementById('broadcastMedia').value = '';
    } catch (error) {
        console.error('Error sending broadcast:', error);
        showNotification('Ошибка отправки рассылки', 'error');
    }
}

// Утилиты
function showLoader() {
    const loader = document.getElementById('loader');
    if (loader) {
        loader.style.display = 'block';
    }
}

function hideLoader() {
    const loader = document.getElementById('loader');
    if (loader) {
        loader.style.display = 'none';
    }
}

function showNotification(message, type = 'info') {
    // Создаем уведомление
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Добавляем стили
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : type === 'warning' ? '#ffc107' : '#17a2b8'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Удаляем через 5 секунд
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function checkAuth() {
    // Проверяем сохраненную сессию
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
    }
}

// Обработка загрузки файлов
function uploadPoemFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.doc,.docx,.pdf,.txt';
    input.onchange = handleFileUpload;
    input.click();
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/admin/upload-poem`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showNotification('Файл загружен и обработан успешно', 'success');
            loadAdminPoems();
            loadPoems();
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        showNotification('Ошибка загрузки файла', 'error');
    }
}

// Обработка изменения типа рассылки
document.getElementById('broadcastType')?.addEventListener('change', function() {
    const mediaGroup = document.getElementById('broadcastMediaGroup');
    if (this.value === 'text') {
        mediaGroup.style.display = 'none';
    } else {
        mediaGroup.style.display = 'block';
    }
});

// Добавляем стили для уведомлений
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .notification-content button {
        background: none;
        border: none;
        color: white;
        font-size: 1.2rem;
        cursor: pointer;
        padding: 0;
        margin-left: 10px;
    }
`;
document.head.appendChild(notificationStyles);