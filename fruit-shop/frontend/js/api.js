// API 配置
const API_BASE = '/api';

// Token 管理 (前端專用 - 使用不同的 key 避免與後台衝突)
const TokenManager = {
    get() {
        return localStorage.getItem('frontend_auth_token');
    },
    set(token) {
        localStorage.setItem('frontend_auth_token', token);
    },
    remove() {
        localStorage.removeItem('frontend_auth_token');
    },
    getUser() {
        const userStr = localStorage.getItem('frontend_user_info');
        return userStr ? JSON.parse(userStr) : null;
    },
    setUser(user) {
        localStorage.setItem('frontend_user_info', JSON.stringify(user));
    },
    removeUser() {
        localStorage.removeItem('frontend_user_info');
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
        },
        async cancel(id, cancel_reason) {
            return apiRequest(`/orders/${id}/cancel`, {
                method: 'PUT',
                body: { cancel_reason }
            });
        },
        async getHistory() {
            return apiRequest('/orders/history/summary');
        },
        async getDetail(id) {
            return apiRequest(`/orders/${id}`);
        },
        async delete(id) {
            return apiRequest(`/orders/${id}`, {
                method: 'DELETE'
            });
        },
        async clearAll() {
            return apiRequest('/orders/clear/all', {
                method: 'DELETE'
            });
        }
    },

    // 收藏
    favorites: {
        async getAll() {
            return apiRequest('/favorites');
        },
        async check(productId) {
            return apiRequest(`/favorites/check/${productId}`);
        },
        async add(product_id) {
            return apiRequest('/favorites', {
                method: 'POST',
                body: { product_id }
            });
        },
        async remove(productId) {
            return apiRequest(`/favorites/${productId}`, {
                method: 'DELETE'
            });
        },
        async toggle(product_id) {
            return apiRequest('/favorites/toggle', {
                method: 'POST',
                body: { product_id }
            });
        }
    }
};

// 匯出
window.API = API;
window.TokenManager = TokenManager;

