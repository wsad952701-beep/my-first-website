// API 配置
const API_BASE = '/api';

// Token 管理
const TokenManager = {
    get() {
        return localStorage.getItem('auth_token');
    },
    set(token) {
        localStorage.setItem('auth_token', token);
    },
    remove() {
        localStorage.removeItem('auth_token');
    },
    getUser() {
        const userStr = localStorage.getItem('user_info');
        return userStr ? JSON.parse(userStr) : null;
    },
    setUser(user) {
        localStorage.setItem('user_info', JSON.stringify(user));
    },
    removeUser() {
        localStorage.removeItem('user_info');
    },
    isLoggedIn() {
        return !!this.get();
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
            throw new Error(data.error || '請求失敗');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// API 物件
const API = {
    // 認證
    auth: {
        async register(userData) {
            const data = await apiRequest('/auth/register', {
                method: 'POST',
                body: userData
            });
            TokenManager.set(data.token);
            TokenManager.setUser(data.user);
            return data;
        },
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
            window.location.href = '/frontend/';
        },
        async getProfile() {
            return apiRequest('/auth/profile');
        },
        async updateProfile(data) {
            return apiRequest('/auth/profile', {
                method: 'PUT',
                body: data
            });
        }
    },

    // 產品
    products: {
        async getCategories() {
            return apiRequest('/products/categories');
        },
        async getAll(params = {}) {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/products${query ? `?${query}` : ''}`);
        },
        async getById(id) {
            return apiRequest(`/products/${id}`);
        },
        async getFeatured() {
            return apiRequest('/products/featured');
        },
        async getSeasonal() {
            return apiRequest('/products/seasonal');
        }
    },

    // 購物車
    cart: {
        async get() {
            return apiRequest('/cart');
        },
        async add(product_id, quantity = 1) {
            return apiRequest('/cart', {
                method: 'POST',
                body: { product_id, quantity }
            });
        },
        async update(item_id, quantity) {
            return apiRequest(`/cart/${item_id}`, {
                method: 'PUT',
                body: { quantity }
            });
        },
        async remove(item_id) {
            return apiRequest(`/cart/${item_id}`, {
                method: 'DELETE'
            });
        },
        async clear() {
            return apiRequest('/cart/clear', {
                method: 'DELETE'
            });
        }
    },

    // 訂單
    orders: {
        async create(orderData) {
            return apiRequest('/orders', {
                method: 'POST',
                body: orderData
            });
        },
        async getAll() {
            return apiRequest('/orders');
        },
        async getById(id) {
            return apiRequest(`/orders/${id}`);
        }
    }
};

// 匯出
window.API = API;
window.TokenManager = TokenManager;
