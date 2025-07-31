// Global variables
let poems = [];
let authors = [];
let currentPoem = null;
let isAdmin = false;

// Initialize the application
function initializeApp() {
    setupEventListeners();
    showTab('home');
    loadInitialData();
}

// Setup all event listeners
function setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            showTab(tabName);
            
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Search and filter functionality
    document.getElementById('poemSearch')?.addEventListener('input', filterPoems);
    document.getElementById('genreFilter')?.addEventListener('change', filterPoems);
    document.getElementById('authorFilter')?.addEventListener('change', filterPoems);
    
    document.getElementById('authorSearch')?.addEventListener('input', filterAuthors);
    document.getElementById('countryFilter')?.addEventListener('change', filterAuthors);
    document.getElementById('periodFilter')?.addEventListener('change', filterAuthors);

    // Admin panel navigation
    document.querySelectorAll('.admin-nav-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const panel = this.getAttribute('data-panel');
            if (panel) {
                switchAdminPanel(panel);
            }
        });
    });

    // Modal functionality
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });

    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });

    // Form submissions
    document.getElementById('submitPoemForm')?.addEventListener('submit', handlePoemSubmission);
    document.getElementById('addPoemForm')?.addEventListener('submit', handleAddPoem);
    document.getElementById('addAuthorForm')?.addEventListener('submit', handleAddAuthor);

    // File upload handling
    document.getElementById('poemFile')?.addEventListener('change', handleFileUpload);
    document.getElementById('broadcastType')?.addEventListener('change', handleBroadcastTypeChange);
}

// Show specific tab
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Load tab-specific data
    switch(tabName) {
        case 'poems':
            loadPoems();
            break;
        case 'authors':
            loadAuthors();
            break;
        case 'library':
            loadLibrary();
            break;
        case 'admin':
            if (isAdmin) {
                loadAdminData();
            }
            break;
    }
}

// Load initial data
async function loadInitialData() {
    try {
        const [poemsData, authorsData] = await Promise.all([
            apiRequest('/api/poems'),
            apiRequest('/api/authors')
        ]);
        
        poems = poemsData;
        authors = authorsData;
        
        updateAuthorFilter();
    } catch (error) {
        console.error('Error loading initial data:', error);
        showNotification('Ошибка загрузки данных', 'error');
    }
}

// API request helper
async function apiRequest(endpoint, options = {}) {
    showLoader();
    
    try {
        const response = await fetch(`http://localhost:5000${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        hideLoader();
        return data;
    } catch (error) {
        hideLoader();
        console.error('API request failed:', error);
        showNotification('Ошибка соединения с сервером', 'error');
        throw error;
    }
}

// Loader functions
function showLoader() {
    document.getElementById('loader').style.display = 'block';
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
}

// Load poems
async function loadPoems() {
    try {
        const data = await apiRequest('/api/poems');
        renderPoems(data);
    } catch (error) {
        console.error('Error loading poems:', error);
    }
}

// Render poems
function renderPoems(poemsData) {
    const grid = document.getElementById('poemsGrid');
    if (!grid) return;

    grid.innerHTML = poemsData.map(poem => `
        <div class="poem-card" onclick="showPoemModal(${JSON.stringify(poem).replace(/"/g, '&quot;')})">
            <h3>${poem.title}</h3>
            <p><strong>Автор:</strong> ${poem.author_name}</p>
            <p><strong>Жанр:</strong> ${poem.genre || 'Не указан'}</p>
            <div class="poem-preview">${poem.text.substring(0, 150)}...</div>
        </div>
    `).join('');
}

// Load authors
async function loadAuthors() {
    try {
        const data = await apiRequest('/api/authors');
        renderAuthors(data);
    } catch (error) {
        console.error('Error loading authors:', error);
    }
}

// Render authors
function renderAuthors(authorsData) {
    const grid = document.getElementById('authorsGrid');
    if (!grid) return;

    grid.innerHTML = authorsData.map(author => `
        <div class="author-card" onclick="showAuthorPoems(${JSON.stringify(author).replace(/"/g, '&quot;')})">
            <h3>${author.name}</h3>
            <p><strong>Страна:</strong> ${author.country || 'Не указана'}</p>
            <p><strong>Период:</strong> ${author.period || 'Не указан'}</p>
            <p><strong>Стихотворений:</strong> ${author.poem_count || 0}</p>
        </div>
    `).join('');
}

// Update author filter dropdown
function updateAuthorFilter() {
    const authorFilter = document.getElementById('authorFilter');
    if (!authorFilter) return;

    const currentValue = authorFilter.value;
    authorFilter.innerHTML = '<option value="">Все авторы</option>';
    
    authors.forEach(author => {
        const option = document.createElement('option');
        option.value = author.name;
        option.textContent = author.name;
        authorFilter.appendChild(option);
    });

    if (currentValue) {
        authorFilter.value = currentValue;
    }
}

// Filter poems
function filterPoems() {
    const searchTerm = document.getElementById('poemSearch')?.value.toLowerCase() || '';
    const genreFilter = document.getElementById('genreFilter')?.value || '';
    const authorFilter = document.getElementById('authorFilter')?.value || '';

    const filteredPoems = poems.filter(poem => {
        const matchesSearch = poem.title.toLowerCase().includes(searchTerm) ||
                            poem.author_name.toLowerCase().includes(searchTerm) ||
                            poem.text.toLowerCase().includes(searchTerm);
        const matchesGenre = !genreFilter || poem.genre === genreFilter;
        const matchesAuthor = !authorFilter || poem.author_name === authorFilter;

        return matchesSearch && matchesGenre && matchesAuthor;
    });

    renderPoems(filteredPoems);
}

// Filter authors
function filterAuthors() {
    const searchTerm = document.getElementById('authorSearch')?.value.toLowerCase() || '';
    const countryFilter = document.getElementById('countryFilter')?.value || '';
    const periodFilter = document.getElementById('periodFilter')?.value || '';

    const filteredAuthors = authors.filter(author => {
        const matchesSearch = author.name.toLowerCase().includes(searchTerm);
        const matchesCountry = !countryFilter || author.country === countryFilter;
        const matchesPeriod = !periodFilter || author.period === periodFilter;

        return matchesSearch && matchesCountry && matchesPeriod;
    });

    renderAuthors(filteredAuthors);
}

// Show poem modal
function showPoemModal(poem) {
    currentPoem = poem;
    
    document.getElementById('modalPoemTitle').textContent = poem.title;
    document.getElementById('modalPoemAuthor').textContent = `Автор: ${poem.author_name}`;
    document.getElementById('modalPoemText').textContent = poem.text;
    
    document.getElementById('poemModal').style.display = 'block';
}

// Save poem to library
async function saveToLibrary() {
    if (!currentPoem) return;

    try {
        const response = await apiRequest(`/api/library/1`, {
            method: 'POST',
            body: JSON.stringify({
                poem_id: currentPoem.id,
                user_id: 1 // Demo user ID
            })
        });

        if (response.message) {
            showNotification('Стихотворение добавлено в библиотеку!', 'success');
        }
    } catch (error) {
        console.error('Error saving to library:', error);
        showNotification('Ошибка при сохранении', 'error');
    }
}

// Share poem
function sharePoem() {
    if (!currentPoem) return;

    const text = `${currentPoem.title}\n\n${currentPoem.text}\n\nАвтор: ${currentPoem.author_name}\n\nПоделиться через Рильке`;
    
    if (navigator.share) {
        navigator.share({
            title: currentPoem.title,
            text: text
        });
    } else {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Стихотворение скопировано в буфер обмена!', 'success');
        });
    }
}

// Show author poems
function showAuthorPoems(author) {
    const authorPoems = poems.filter(poem => poem.author_name === author.name);
    renderPoems(authorPoems);
    showTab('poems');
}

// Load library
async function loadLibrary() {
    try {
        const data = await apiRequest('/api/library/1');
        renderLibraryPoems(data);
        updateLibraryStats();
    } catch (error) {
        console.error('Error loading library:', error);
    }
}

// Render library poems
function renderLibraryPoems(libraryData) {
    const container = document.getElementById('libraryPoems');
    if (!container) return;

    if (libraryData.length === 0) {
        container.innerHTML = `
            <div class="text-center">
                <p style="color: rgba(255, 255, 255, 0.8);">Ваша библиотека пуста</p>
                <button class="btn btn-primary" onclick="showTab('poems')">
                    Найти стихотворения
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = libraryData.map(poem => `
        <div class="poem-card" onclick="showPoemModal(${JSON.stringify(poem).replace(/"/g, '&quot;')})">
            <h3>${poem.title}</h3>
            <p><strong>Автор:</strong> ${poem.author_name}</p>
            <p><strong>Жанр:</strong> ${poem.genre || 'Не указан'}</p>
            <div class="poem-preview">${poem.text.substring(0, 150)}...</div>
        </div>
    `).join('');
}

// Update library stats
function updateLibraryStats() {
    // Demo stats
    document.getElementById('savedPoemsCount').textContent = '5';
    document.getElementById('quotesCount').textContent = '12';
}

// Get random poem
async function getRandomPoem() {
    try {
        const poem = await apiRequest('/api/poems/random');
        showPoemModal(poem);
    } catch (error) {
        console.error('Error getting random poem:', error);
        showNotification('Ошибка при получении случайного стихотворения', 'error');
    }
}

// Scroll to section
function scrollToSection(sectionId) {
    showTab(sectionId);
    document.getElementById(sectionId).scrollIntoView({ behavior: 'smooth' });
}

// Admin functionality
function adminLogin() {
    const username = document.getElementById('adminUsername').value;
    const password = document.getElementById('adminPassword').value;

    if (username === 'admin' && password === 'admin') {
        isAdmin = true;
        document.getElementById('adminLogin').style.display = 'none';
        document.getElementById('adminDashboard').style.display = 'block';
        loadAdminData();
        showNotification('Успешный вход в админ-панель', 'success');
    } else {
        showNotification('Неверные учетные данные', 'error');
    }
}

function adminLogout() {
    isAdmin = false;
    document.getElementById('adminLogin').style.display = 'block';
    document.getElementById('adminDashboard').style.display = 'none';
    document.getElementById('adminUsername').value = '';
    document.getElementById('adminPassword').value = '';
    showNotification('Выход из админ-панели', 'success');
}

function switchAdminPanel(panelName) {
    // Update navigation buttons
    document.querySelectorAll('.admin-nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Show selected panel
    document.querySelectorAll('.admin-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(panelName + 'Panel').classList.add('active');

    // Load panel-specific data
    switch(panelName) {
        case 'stats':
            loadAdminStats();
            break;
        case 'poems':
            loadAdminPoems();
            break;
        case 'authors':
            loadAdminAuthors();
            break;
        case 'submissions':
            loadAdminSubmissions();
            break;
    }
}

async function loadAdminData() {
    await Promise.all([
        loadAdminStats(),
        loadAdminPoems(),
        loadAdminAuthors(),
        loadAdminSubmissions()
    ]);
}

async function loadAdminStats() {
    try {
        const stats = await apiRequest('/api/admin/stats');
        document.getElementById('totalUsers').textContent = stats.total_users || 0;
        document.getElementById('totalPoems').textContent = stats.total_poems || 0;
        document.getElementById('totalAuthors').textContent = stats.total_authors || 0;
        document.getElementById('pendingSubmissions').textContent = stats.pending_submissions || 0;
    } catch (error) {
        console.error('Error loading admin stats:', error);
    }
}

async function loadAdminPoems() {
    try {
        const poems = await apiRequest('/api/admin/poems');
        renderAdminPoems(poems);
    } catch (error) {
        console.error('Error loading admin poems:', error);
    }
}

function renderAdminPoems(poemsData) {
    const tbody = document.querySelector('#poemsTable tbody');
    if (!tbody) return;

    tbody.innerHTML = poemsData.map(poem => `
        <tr>
            <td>${poem.id}</td>
            <td>${poem.title}</td>
            <td>${poem.author_name}</td>
            <td>${poem.genre || 'Не указан'}</td>
            <td>
                <button class="action-btn btn-edit" onclick="editPoem(${poem.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn btn-delete" onclick="deletePoem(${poem.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function loadAdminAuthors() {
    try {
        const authors = await apiRequest('/api/admin/authors');
        renderAdminAuthors(authors);
    } catch (error) {
        console.error('Error loading admin authors:', error);
    }
}

function renderAdminAuthors(authorsData) {
    const tbody = document.querySelector('#authorsTable tbody');
    if (!tbody) return;

    tbody.innerHTML = authorsData.map(author => `
        <tr>
            <td>${author.id}</td>
            <td>${author.name}</td>
            <td>${author.country || 'Не указана'}</td>
            <td>${author.period || 'Не указан'}</td>
            <td>
                <button class="action-btn btn-edit" onclick="editAuthor(${author.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn btn-delete" onclick="deleteAuthor(${author.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function loadAdminSubmissions() {
    try {
        const submissions = await apiRequest('/api/admin/submissions');
        renderAdminSubmissions(submissions);
    } catch (error) {
        console.error('Error loading admin submissions:', error);
    }
}

function renderAdminSubmissions(submissionsData) {
    const container = document.getElementById('submissionsList');
    if (!container) return;

    if (submissionsData.length === 0) {
        container.innerHTML = '<p style="color: rgba(255, 255, 255, 0.8);">Нет предложений для модерации</p>';
        return;
    }

    container.innerHTML = submissionsData.map(submission => `
        <div class="submission-item">
            <div class="submission-header">
                <span class="submission-user">Пользователь ${submission.user_id}</span>
                <span class="submission-date">${new Date(submission.created_at).toLocaleDateString()}</span>
            </div>
            <div class="submission-content">
                <strong>Название:</strong> ${submission.title}<br>
                <strong>Автор:</strong> ${submission.author_name}<br>
                <strong>Жанр:</strong> ${submission.genre || 'Не указан'}<br>
                <strong>Текст:</strong><br>
                ${submission.text.substring(0, 200)}...
            </div>
            <div class="submission-actions">
                <button class="btn btn-primary" onclick="approveSubmission(${submission.id})">
                    <i class="fas fa-check"></i>
                    Одобрить
                </button>
                <button class="btn btn-secondary" onclick="rejectSubmission(${submission.id})">
                    <i class="fas fa-times"></i>
                    Отклонить
                </button>
            </div>
        </div>
    `).join('');
}

// Admin actions
function editPoem(poemId) {
    showNotification('Функция редактирования в разработке', 'info');
}

function editAuthor(authorId) {
    showNotification('Функция редактирования в разработке', 'info');
}

async function deletePoem(poemId) {
    if (!confirm('Вы уверены, что хотите удалить это стихотворение?')) return;

    try {
        await apiRequest(`/api/admin/poems/${poemId}`, { method: 'DELETE' });
        showNotification('Стихотворение удалено', 'success');
        loadAdminPoems();
    } catch (error) {
        console.error('Error deleting poem:', error);
        showNotification('Ошибка при удалении', 'error');
    }
}

async function deleteAuthor(authorId) {
    if (!confirm('Вы уверены, что хотите удалить этого автора?')) return;

    try {
        await apiRequest(`/api/admin/authors/${authorId}`, { method: 'DELETE' });
        showNotification('Автор удален', 'success');
        loadAdminAuthors();
    } catch (error) {
        console.error('Error deleting author:', error);
        showNotification('Ошибка при удалении', 'error');
    }
}

async function approveSubmission(submissionId) {
    try {
        await apiRequest(`/api/admin/submissions/${submissionId}/approve`, { method: 'POST' });
        showNotification('Предложение одобрено', 'success');
        loadAdminSubmissions();
    } catch (error) {
        console.error('Error approving submission:', error);
        showNotification('Ошибка при одобрении', 'error');
    }
}

async function rejectSubmission(submissionId) {
    try {
        await apiRequest(`/api/admin/submissions/${submissionId}/reject`, { method: 'POST' });
        showNotification('Предложение отклонено', 'success');
        loadAdminSubmissions();
    } catch (error) {
        console.error('Error rejecting submission:', error);
        showNotification('Ошибка при отклонении', 'error');
    }
}

// Poem submission handling
async function handlePoemSubmission(e) {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('title', document.getElementById('poemTitle').value);
    formData.append('author_name', document.getElementById('poemAuthor').value);
    formData.append('genre', document.getElementById('poemGenre').value);
    formData.append('text', document.getElementById('poemText').value);
    
    const file = document.getElementById('poemFile').files[0];
    if (file) {
        formData.append('file', file);
    }

    try {
        showLoader();
        const response = await fetch('http://localhost:5000/api/submit-poem', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            showNotification('Стихотворение отправлено на модерацию!', 'success');
            clearPoemForm();
        } else {
            throw new Error('Ошибка отправки');
        }
    } catch (error) {
        console.error('Error submitting poem:', error);
        showNotification('Ошибка при отправке стихотворения', 'error');
    } finally {
        hideLoader();
    }
}

function clearPoemForm() {
    document.getElementById('submitPoemForm').reset();
}

function handleFileUpload(e) {
    const file = e.target.files[0];
    if (file) {
        showNotification(`Файл "${file.name}" загружен`, 'success');
    }
}

// Broadcast functionality
function handleBroadcastTypeChange(e) {
    const mediaInput = document.getElementById('mediaInput');
    const broadcastType = e.target.value;
    
    if (broadcastType === 'text') {
        mediaInput.style.display = 'none';
    } else {
        mediaInput.style.display = 'block';
    }
}

async function sendBroadcast() {
    const type = document.getElementById('broadcastType').value;
    const text = document.getElementById('broadcastText').value;
    const media = document.getElementById('broadcastMedia').files[0];

    if (!text.trim()) {
        showNotification('Введите текст сообщения', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('type', type);
    formData.append('text', text);
    if (media) {
        formData.append('media', media);
    }

    try {
        showLoader();
        const response = await fetch('http://localhost:5000/api/admin/broadcast', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            showNotification('Рассылка отправлена!', 'success');
            document.getElementById('broadcastText').value = '';
            document.getElementById('broadcastMedia').value = '';
        } else {
            throw new Error('Ошибка отправки рассылки');
        }
    } catch (error) {
        console.error('Error sending broadcast:', error);
        showNotification('Ошибка при отправке рассылки', 'error');
    } finally {
        hideLoader();
    }
}

// Modal functions
function showAddPoemForm() {
    document.getElementById('addPoemModal').style.display = 'block';
}

function showAddAuthorForm() {
    document.getElementById('addAuthorModal').style.display = 'block';
}

async function handleAddPoem(e) {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('title', document.getElementById('poemTitle').value);
    formData.append('author_id', document.getElementById('poemAuthor').value);
    formData.append('genre', document.getElementById('poemGenre').value);
    formData.append('text', document.getElementById('poemText').value);
    
    const file = document.getElementById('poemFile').files[0];
    if (file) {
        formData.append('file', file);
    }

    try {
        showLoader();
        const response = await fetch('http://localhost:5000/api/admin/upload-poem', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            showNotification('Стихотворение добавлено!', 'success');
            document.getElementById('addPoemModal').style.display = 'none';
            loadAdminPoems();
        } else {
            throw new Error('Ошибка добавления');
        }
    } catch (error) {
        console.error('Error adding poem:', error);
        showNotification('Ошибка при добавлении стихотворения', 'error');
    } finally {
        hideLoader();
    }
}

async function handleAddAuthor(e) {
    e.preventDefault();
    
    const authorData = {
        name: document.getElementById('authorName').value,
        country: document.getElementById('authorCountry').value,
        period: document.getElementById('authorPeriod').value
    };

    try {
        await apiRequest('/api/admin/authors', {
            method: 'POST',
            body: JSON.stringify(authorData)
        });
        
        showNotification('Автор добавлен!', 'success');
        document.getElementById('addAuthorModal').style.display = 'none';
        loadAdminAuthors();
    } catch (error) {
        console.error('Error adding author:', error);
        showNotification('Ошибка при добавлении автора', 'error');
    }
}

// Utility functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `message ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);