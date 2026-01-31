// Admin API 配置
const API_BASE = '/api';

// Token 管理 (後台專用 - 使用不同的 key 避免與前端衝突)
const TokenManager = {
    get() {
        return localStorage.getItem('admin_auth_token');
    },
    set(token) {
        localStorage.setItem('admin_auth_token', token);
    },
    remove() {
        localStorage.removeItem('admin_auth_token');
    },
    getUser() {
        const userStr = localStorage.getItem('admin_user_info');
        return userStr ? JSON.parse(userStr) : null;
    },
    setUser(user) {
        localStorage.setItem('admin_user_info', JSON.stringify(user));
    },
    removeUser() {
        localStorage.removeItem('admin_user_info');
    },
    isLoggedIn() {
        return !!this.get();
    },
    isAdmin() {
        const user = this.getUser();
        return user && user.is_admin;
    }
};

// API 請求封裝
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const token = TokenManager.get();

    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        },
        ...options
    };

    if (options.body && typeof options.body === 'object') {
        config.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                TokenManager.remove();
                TokenManager.removeUser();
                window.location.href = '/admin/';
            }
            throw new Error(data.error || '請求失敗');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Admin API
const AdminAPI = {
    // 認證
    auth: {
        async login(email, password) {
            const data = await apiRequest('/auth/login', {
                method: 'POST',
                body: { email, password }
            });
            TokenManager.set(data.token);
            TokenManager.setUser(data.user);
            return data;
        },
        logout() {
            TokenManager.remove();
            TokenManager.removeUser();
            window.location.href = '/admin/';
        }
    },

    // 儀表板
    dashboard: {
        async get() {
            return apiRequest('/admin/dashboard');
        }
    },

    // 訂單
    orders: {
        async getAll(params = {}) {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/admin/orders${query ? `?${query}` : ''}`);
        },
        async getById(id) {
            return apiRequest(`/admin/orders/${id}`);
        },
        async updateStatus(id, status, options = {}) {
            return apiRequest(`/admin/orders/${id}/status`, {
                method: 'PUT',
                body: { status, cancel_reason: options.cancel_reason, admin_note: options.admin_note }
            });
        }
    },

    // 產品
    products: {
        async getAll() {
            return apiRequest('/admin/products');
        },
        async create(product) {
            return apiRequest('/admin/products', {
                method: 'POST',
                body: product
            });
        },
        async update(id, product) {
            return apiRequest(`/admin/products/${id}`, {
                method: 'PUT',
                body: product
            });
        },
        async delete(id) {
            return apiRequest(`/admin/products/${id}`, {
                method: 'DELETE'
            });
        }
    },

    // 會員
    members: {
        async getAll(params = {}) {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/admin/members${query ? `?${query}` : ''}`);
        },
        async updateStatus(memberId, status) {
            return apiRequest(`/admin/members/${memberId}/status`, {
                method: 'PUT',
                body: { status }
            });
        },
        async updateCredit(memberId, data) {
            return apiRequest(`/admin/members/${memberId}/credit`, {
                method: 'PUT',
                body: data
            });
        },
        async delete(memberId) {
            return apiRequest(`/admin/members/${memberId}`, {
                method: 'DELETE'
            });
        }
    },

    // 分類
    categories: {
        async getAll() {
            return apiRequest('/admin/categories');
        }
    }
};

// 工具函數
function formatPrice(price) {
    return new Intl.NumberFormat('zh-TW', {
        style: 'currency',
        currency: 'TWD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(price);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getStatusText(status) {
    const statusMap = {
        'pending': '待處理',
        'processing': '處理中',
        'shipped': '已出貨',
        'completed': '已完成',
        'cancelled': '已取消'
    };
    return statusMap[status] || status;
}

// Toast 訊息
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 檢查管理員權限
function checkAdminAuth() {
    if (!TokenManager.isLoggedIn() || !TokenManager.isAdmin()) {
        window.location.href = '/admin/';
        return false;
    }
    return true;
}

// 初始化側邊欄
function initSidebar() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href && href.includes(currentPage)) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// 初始化登出按鈕
function initLogout() {
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            AdminAPI.auth.logout();
        });
    }
}

// 頁面初始化
document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initLogout();
});

// 匯出
window.AdminAPI = AdminAPI;
window.TokenManager = TokenManager;
window.formatPrice = formatPrice;
window.formatDate = formatDate;
window.getStatusText = getStatusText;
window.showToast = showToast;
window.checkAdminAuth = checkAdminAuth;
