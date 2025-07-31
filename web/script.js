// Global variables
let currentUser = null;
let poems = [];
let authors = [];
let currentPoem = null;
let isAdmin = false;

// API endpoint
const API_BASE = 'http://localhost:5000/api';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    setupMobileMenu();
    setupSmoothScrolling();
    setupModals();
    setupForms();
    
    // Load initial data
    loadPoems();
    loadAuthors();
    loadStats();
});

// Initialize application
function initializeApp() {
    // Check if user is admin (simple check for demo)
    const adminParam = new URLSearchParams(window.location.search).get('admin');
    if (adminParam === 'true') {
        isAdmin = true;
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
    }
    
    // Show home tab by default
    showTab('home');
}

// Setup event listeners
function setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            showTab(tabName);
            
            // Update active nav link
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Search functionality
    const poemSearch = document.getElementById('poemSearch');
    if (poemSearch) {
        poemSearch.addEventListener('input', debounce(function() {
            searchPoems();
        }, 300));
    }
    
    const authorSearch = document.getElementById('authorSearch');
    if (authorSearch) {
        authorSearch.addEventListener('input', debounce(function() {
            searchAuthors();
        }, 300));
    }
    
    // Filter functionality
    const genreFilter = document.getElementById('genreFilter');
    if (genreFilter) {
        genreFilter.addEventListener('change', function() {
            filterPoems();
        });
    }
    
    const authorFilter = document.getElementById('authorFilter');
    if (authorFilter) {
        authorFilter.addEventListener('change', function() {
            filterPoems();
        });
    }
    
    // Admin panel navigation
    document.querySelectorAll('.admin-nav-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const panel = this.getAttribute('data-panel');
            if (panel) {
                switchAdminPanel(panel);
            }
        });
    });
    
    // Admin forms
    const addPoemForm = document.getElementById('addPoemForm');
    if (addPoemForm) {
        addPoemForm.addEventListener('submit', handleAddPoem);
    }
    
    const addAuthorForm = document.getElementById('addAuthorForm');
    if (addAuthorForm) {
        addAuthorForm.addEventListener('submit', handleAddAuthor);
    }
    
    // Broadcast type change
    const broadcastType = document.getElementById('broadcastType');
    if (broadcastType) {
        broadcastType.addEventListener('change', function() {
            const mediaInput = document.getElementById('mediaInput');
            if (this.value !== 'text') {
                mediaInput.style.display = 'block';
            } else {
                mediaInput.style.display = 'none';
            }
        });
    }
}

// Show specific tab
function showTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
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

// Setup mobile menu
function setupMobileMenu() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
}

// Setup smooth scrolling
function setupSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Setup modals
function setupModals() {
    // Close modal on X click
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });
    
    // Close modal on outside click
    window.addEventListener('click', function(event) {
        document.querySelectorAll('.modal').forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// Setup forms
function setupForms() {
    // File upload handling
    const poemFile = document.getElementById('poemFile');
    if (poemFile) {
        poemFile.addEventListener('change', handleFileUpload);
    }
}

// API request helper
async function apiRequest(endpoint, options = {}) {
    try {
        showLoader();
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        showNotification('Ошибка при загрузке данных', 'error');
        throw error;
    } finally {
        hideLoader();
    }
}

// Load poems
async function loadPoems() {
    try {
        const data = await apiRequest('/poems');
        poems = data;
        renderPoems(poems);
        updateAuthorFilter();
    } catch (error) {
        console.error('Failed to load poems:', error);
    }
}

// Load authors
async function loadAuthors() {
    try {
        const data = await apiRequest('/authors');
        authors = data;
        renderAuthors(authors);
    } catch (error) {
        console.error('Failed to load authors:', error);
    }
}

// Load stats
async function loadStats() {
    try {
        const data = await apiRequest('/stats');
        updateStats(data);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Render poems
function renderPoems(poemsToRender) {
    const grid = document.getElementById('poemsGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    poemsToRender.forEach(poem => {
        const card = document.createElement('div');
        card.className = 'poem-card';
        card.onclick = () => showPoemModal(poem);
        
        card.innerHTML = `
            <h3>${poem.title}</h3>
            <p>${poem.author_name || 'Неизвестный автор'}</p>
            <div class="poem-preview">${poem.text.substring(0, 150)}...</div>
        `;
        
        grid.appendChild(card);
    });
}

// Render authors
function renderAuthors(authorsToRender) {
    const grid = document.getElementById('authorsGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    authorsToRender.forEach(author => {
        const card = document.createElement('div');
        card.className = 'author-card';
        card.onclick = () => showAuthorPoems(author);
        
        card.innerHTML = `
            <h3>${author.name}</h3>
            <p>${author.country || 'Неизвестная страна'}</p>
            <p>${author.period || 'Неизвестный период'}</p>
        `;
        
        grid.appendChild(card);
    });
}

// Update stats
function updateStats(stats) {
    document.getElementById('totalUsers').textContent = stats.users || 0;
    document.getElementById('totalPoems').textContent = stats.poems || 0;
    document.getElementById('totalAuthors').textContent = stats.authors || 0;
    document.getElementById('pendingSubmissions').textContent = stats.pending_submissions || 0;
}

// Search poems
function searchPoems() {
    const searchTerm = document.getElementById('poemSearch').value.toLowerCase();
    const filteredPoems = poems.filter(poem => 
        poem.title.toLowerCase().includes(searchTerm) ||
        (poem.author_name && poem.author_name.toLowerCase().includes(searchTerm))
    );
    renderPoems(filteredPoems);
}

// Search authors
function searchAuthors() {
    const searchTerm = document.getElementById('authorSearch').value.toLowerCase();
    const filteredAuthors = authors.filter(author => 
        author.name.toLowerCase().includes(searchTerm)
    );
    renderAuthors(filteredAuthors);
}

// Filter poems
function filterPoems() {
    const genreFilter = document.getElementById('genreFilter').value;
    const authorFilter = document.getElementById('authorFilter').value;
    
    let filteredPoems = poems;
    
    if (genreFilter) {
        filteredPoems = filteredPoems.filter(poem => poem.genre === genreFilter);
    }
    
    if (authorFilter) {
        filteredPoems = filteredPoems.filter(poem => poem.author_id == authorFilter);
    }
    
    renderPoems(filteredPoems);
}

// Update author filter
function updateAuthorFilter() {
    const authorFilter = document.getElementById('authorFilter');
    if (!authorFilter) return;
    
    const uniqueAuthors = [...new Set(poems.map(poem => poem.author_name).filter(Boolean))];
    
    authorFilter.innerHTML = '<option value="">Все авторы</option>';
    uniqueAuthors.forEach(author => {
        const option = document.createElement('option');
        option.value = author;
        option.textContent = author;
        authorFilter.appendChild(option);
    });
}

// Get random poem
async function getRandomPoem() {
    try {
        const data = await apiRequest('/poems/random');
        if (data) {
            showPoemModal(data);
        }
    } catch (error) {
        console.error('Failed to get random poem:', error);
    }
}

// Show poem modal
function showPoemModal(poem) {
    currentPoem = poem;
    
    document.getElementById('modalPoemTitle').textContent = poem.title;
    document.getElementById('modalPoemAuthor').textContent = poem.author_name || 'Неизвестный автор';
    document.getElementById('modalPoemText').textContent = poem.text;
    
    document.getElementById('poemModal').style.display = 'block';
}

// Save to library
async function saveToLibrary() {
    if (!currentPoem) return;
    
    try {
        await apiRequest('/library/save', {
            method: 'POST',
            body: JSON.stringify({
                poem_id: currentPoem.id,
                user_id: 1 // Demo user ID
            })
        });
        
        showNotification('Стихотворение сохранено в библиотеку!', 'success');
        document.getElementById('poemModal').style.display = 'none';
    } catch (error) {
        console.error('Failed to save to library:', error);
        showNotification('Ошибка при сохранении', 'error');
    }
}

// Share poem
function sharePoem() {
    if (!currentPoem) return;
    
    const shareText = `${currentPoem.title}\n\n${currentPoem.author_name || 'Неизвестный автор'}\n\n${currentPoem.text}\n\nПоделено через Рильке`;
    
    if (navigator.share) {
        navigator.share({
            title: currentPoem.title,
            text: shareText
        });
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(shareText).then(() => {
            showNotification('Стихотворение скопировано в буфер обмена!', 'success');
        });
    }
}

// Show author poems
function showAuthorPoems(author) {
    const authorPoems = poems.filter(poem => poem.author_id === author.id);
    renderPoems(authorPoems);
    showTab('poems');
}

// Load library
async function loadLibrary() {
    try {
        const data = await apiRequest('/library/1'); // Demo user ID
        renderLibraryPoems(data);
        updateLibraryStats(data);
    } catch (error) {
        console.error('Failed to load library:', error);
    }
}

// Render library poems
function renderLibraryPoems(libraryPoems) {
    const container = document.getElementById('libraryPoems');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (libraryPoems.length === 0) {
        container.innerHTML = '<p class="text-center text-white">Ваша библиотека пуста</p>';
        return;
    }
    
    libraryPoems.forEach(poem => {
        const card = document.createElement('div');
        card.className = 'poem-card';
        card.onclick = () => showPoemModal(poem);
        
        card.innerHTML = `
            <h3>${poem.title}</h3>
            <p>${poem.author_name || 'Неизвестный автор'}</p>
            <div class="poem-preview">${poem.text.substring(0, 150)}...</div>
        `;
        
        container.appendChild(card);
    });
}

// Update library stats
function updateLibraryStats(libraryPoems) {
    document.getElementById('savedPoemsCount').textContent = libraryPoems.length;
    document.getElementById('quotesCount').textContent = '0'; // Demo value
}

// Admin functions
function adminLogin() {
    const username = document.getElementById('adminUsername').value;
    const password = document.getElementById('adminPassword').value;
    
    // Simple demo login
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
    showNotification('Выход из админ-панели', 'success');
}

function switchAdminPanel(panelName) {
    // Hide all panels
    document.querySelectorAll('.admin-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Show selected panel
    const selectedPanel = document.getElementById(panelName + 'Panel');
    if (selectedPanel) {
        selectedPanel.classList.add('active');
    }
    
    // Update nav buttons
    document.querySelectorAll('.admin-nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.querySelector(`[data-panel="${panelName}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Load panel-specific data
    switch(panelName) {
        case 'stats':
            loadStats();
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

// Load admin data
async function loadAdminData() {
    await Promise.all([
        loadStats(),
        loadAdminPoems(),
        loadAdminAuthors(),
        loadAdminSubmissions()
    ]);
}

// Load admin poems
async function loadAdminPoems() {
    try {
        const data = await apiRequest('/admin/poems');
        renderAdminPoems(data);
    } catch (error) {
        console.error('Failed to load admin poems:', error);
    }
}

// Load admin authors
async function loadAdminAuthors() {
    try {
        const data = await apiRequest('/admin/authors');
        renderAdminAuthors(data);
    } catch (error) {
        console.error('Failed to load admin authors:', error);
    }
}

// Load admin submissions
async function loadAdminSubmissions() {
    try {
        const data = await apiRequest('/admin/submissions');
        renderAdminSubmissions(data);
    } catch (error) {
        console.error('Failed to load admin submissions:', error);
    }
}

// Render admin poems
function renderAdminPoems(poems) {
    const tbody = document.querySelector('#poemsTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    poems.forEach(poem => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${poem.id}</td>
            <td>${poem.title}</td>
            <td>${poem.author_name || 'Неизвестный'}</td>
            <td>${poem.genre || '-'}</td>
            <td>
                <button class="action-btn btn-edit" onclick="editPoem(${poem.id})">Изменить</button>
                <button class="action-btn btn-delete" onclick="deletePoem(${poem.id})">Удалить</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Render admin authors
function renderAdminAuthors(authors) {
    const tbody = document.querySelector('#authorsTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    authors.forEach(author => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${author.id}</td>
            <td>${author.name}</td>
            <td>${author.country || '-'}</td>
            <td>${author.period || '-'}</td>
            <td>
                <button class="action-btn btn-edit" onclick="editAuthor(${author.id})">Изменить</button>
                <button class="action-btn btn-delete" onclick="deleteAuthor(${author.id})">Удалить</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Render admin submissions
function renderAdminSubmissions(submissions) {
    const container = document.getElementById('submissionsList');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (submissions.length === 0) {
        container.innerHTML = '<p class="text-center text-white">Нет предложений на модерации</p>';
        return;
    }
    
    submissions.forEach(submission => {
        const item = document.createElement('div');
        item.className = 'submission-item';
        item.innerHTML = `
            <div class="submission-header">
                <span class="submission-user">ID: ${submission.id}</span>
                <span class="submission-date">${new Date(submission.created_at).toLocaleDateString()}</span>
            </div>
            <div class="submission-content">${submission.text}</div>
            <div class="submission-actions">
                <button class="btn btn-secondary" onclick="approveSubmission(${submission.id})">Одобрить</button>
                <button class="btn btn-secondary" onclick="rejectSubmission(${submission.id})">Отклонить</button>
            </div>
        `;
        container.appendChild(item);
    });
}

// Show add poem form
function showAddPoemForm() {
    document.getElementById('addPoemModal').style.display = 'block';
}

// Show add author form
function showAddAuthorForm() {
    document.getElementById('addAuthorModal').style.display = 'block';
}

// Handle add poem
async function handleAddPoem(e) {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('title', document.getElementById('poemTitle').value);
    formData.append('text', document.getElementById('poemText').value);
    formData.append('author_id', document.getElementById('poemAuthor').value);
    formData.append('genre', document.getElementById('poemGenre').value);
    
    const file = document.getElementById('poemFile').files[0];
    if (file) {
        formData.append('file', file);
    }
    
    try {
        await fetch(`${API_BASE}/admin/upload-poem`, {
            method: 'POST',
            body: formData
        });
        
        showNotification('Стихотворение добавлено!', 'success');
        document.getElementById('addPoemModal').style.display = 'none';
        document.getElementById('addPoemForm').reset();
        loadAdminPoems();
    } catch (error) {
        console.error('Failed to add poem:', error);
        showNotification('Ошибка при добавлении стихотворения', 'error');
    }
}

// Handle add author
async function handleAddAuthor(e) {
    e.preventDefault();
    
    try {
        await apiRequest('/admin/authors', {
            method: 'POST',
            body: JSON.stringify({
                name: document.getElementById('authorName').value,
                country: document.getElementById('authorCountry').value,
                period: document.getElementById('authorPeriod').value
            })
        });
        
        showNotification('Автор добавлен!', 'success');
        document.getElementById('addAuthorModal').style.display = 'none';
        document.getElementById('addAuthorForm').reset();
        loadAdminAuthors();
    } catch (error) {
        console.error('Failed to add author:', error);
        showNotification('Ошибка при добавлении автора', 'error');
    }
}

// Edit poem (placeholder)
function editPoem(poemId) {
    showNotification('Функция редактирования в разработке', 'error');
}

// Edit author (placeholder)
function editAuthor(authorId) {
    showNotification('Функция редактирования в разработке', 'error');
}

// Delete poem
async function deletePoem(poemId) {
    if (!confirm('Вы уверены, что хотите удалить это стихотворение?')) return;
    
    try {
        await apiRequest(`/admin/poems/${poemId}`, {
            method: 'DELETE'
        });
        
        showNotification('Стихотворение удалено!', 'success');
        loadAdminPoems();
    } catch (error) {
        console.error('Failed to delete poem:', error);
        showNotification('Ошибка при удалении стихотворения', 'error');
    }
}

// Delete author
async function deleteAuthor(authorId) {
    if (!confirm('Вы уверены, что хотите удалить этого автора?')) return;
    
    try {
        await apiRequest(`/admin/authors/${authorId}`, {
            method: 'DELETE'
        });
        
        showNotification('Автор удален!', 'success');
        loadAdminAuthors();
    } catch (error) {
        console.error('Failed to delete author:', error);
        showNotification('Ошибка при удалении автора', 'error');
    }
}

// Approve submission
async function approveSubmission(submissionId) {
    try {
        await apiRequest(`/admin/submissions/${submissionId}/approve`, {
            method: 'POST'
        });
        
        showNotification('Предложение одобрено!', 'success');
        loadAdminSubmissions();
    } catch (error) {
        console.error('Failed to approve submission:', error);
        showNotification('Ошибка при одобрении предложения', 'error');
    }
}

// Reject submission
async function rejectSubmission(submissionId) {
    try {
        await apiRequest(`/admin/submissions/${submissionId}/reject`, {
            method: 'POST'
        });
        
        showNotification('Предложение отклонено!', 'success');
        loadAdminSubmissions();
    } catch (error) {
        console.error('Failed to reject submission:', error);
        showNotification('Ошибка при отклонении предложения', 'error');
    }
}

// Send broadcast
async function sendBroadcast() {
    const type = document.getElementById('broadcastType').value;
    const text = document.getElementById('broadcastText').value;
    
    if (!text.trim()) {
        showNotification('Введите текст для рассылки', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('type', type);
        formData.append('text', text);
        
        const file = document.getElementById('broadcastMedia').files[0];
        if (file) {
            formData.append('media', file);
        }
        
        await fetch(`${API_BASE}/admin/broadcast`, {
            method: 'POST',
            body: formData
        });
        
        showNotification('Рассылка отправлена!', 'success');
        document.getElementById('broadcastText').value = '';
        document.getElementById('broadcastMedia').value = '';
    } catch (error) {
        console.error('Failed to send broadcast:', error);
        showNotification('Ошибка при отправке рассылки', 'error');
    }
}

// Handle file upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        // For demo purposes, just show the file name
        showNotification(`Файл "${file.name}" загружен`, 'success');
    };
    reader.readAsText(file);
}

// Load more poems
function loadMorePoems() {
    showNotification('Функция загрузки дополнительных стихотворений в разработке', 'error');
}

// Scroll to section
function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
    }
}

// Utility functions
function showLoader() {
    document.getElementById('loader').style.display = 'block';
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `message ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
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

// Check authentication (demo)
function checkAuth() {
    // Demo authentication check
    return true;
}

// Upload poem file
async function uploadPoemFile() {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.txt,.doc,.docx,.pdf';
    
    fileInput.onchange = async function(event) {
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
                showNotification('Файл успешно загружен и обработан!', 'success');
                loadAdminPoems();
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Failed to upload file:', error);
            showNotification('Ошибка при загрузке файла', 'error');
        }
    };
    
    fileInput.click();
}