// 工具函數

// 格式化價格
function formatPrice(price) {
    return new Intl.NumberFormat('zh-TW', {
        style: 'currency',
        currency: 'TWD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(price);
}

// 格式化日期
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

// 取得狀態文字
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
    // 移除現有的 toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(toast);

    // 顯示動畫
    setTimeout(() => toast.classList.add('show'), 10);

    // 自動關閉
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 產品卡片 HTML
function createProductCard(product) {
    const discount = product.original_price > product.price;

    return `
        <div class="product-card">
            <a href="/frontend/product-detail.html?id=${product.id}" class="product-image">
                ${product.image_url
            ? `<img src="${product.image_url}" alt="${product.name}" onerror="this.parentElement.innerHTML='<div class=\\'product-placeholder\\'>🍎</div>'">`
            : '<div class="product-placeholder">🍎</div>'
        }
                <div class="product-badges">
                    ${product.is_featured ? '<span class="badge badge-hot">🔥 熱賣</span>' : ''}
                    ${product.is_seasonal ? '<span class="badge badge-seasonal">✨ 季節限定</span>' : ''}
                    ${discount ? '<span class="badge badge-sale">特價</span>' : ''}
                </div>
            </a>
            <div class="product-info">
                <div class="product-category">${product.category_name || ''}</div>
                <h3 class="product-name">
                    <a href="/frontend/product-detail.html?id=${product.id}">${product.name}</a>
                </h3>
                <div class="product-price">
                    <span class="current-price">${formatPrice(product.price)}</span>
                    ${discount ? `<span class="original-price">${formatPrice(product.original_price)}</span>` : ''}
                </div>
                <div class="product-actions">
                    <button class="btn btn-primary" onclick="addToCart(${product.id})" ${product.stock <= 0 ? 'disabled' : ''}>
                        <i class="fas fa-cart-plus"></i> 加入購物車
                    </button>
                </div>
            </div>
        </div>
    `;
}

// 加入購物車
async function addToCart(productId) {
    if (!TokenManager.isLoggedIn()) {
        showToast('請先登入會員', 'error');
        setTimeout(() => {
            window.location.href = '/frontend/login.html';
        }, 1500);
        return;
    }

    try {
        await API.cart.add(productId, 1);
        await cart.fetch();
        showToast('已加入購物車', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 更新 Header UI
async function updateHeaderUI() {
    const loginLink = document.querySelector('.login-link');
    const userLink = document.querySelector('.user-link');
    const logoutBtn = document.querySelector('.logout-btn');
    const userName = document.querySelector('.user-name');

    if (TokenManager.isLoggedIn()) {
        const user = TokenManager.getUser();

        if (loginLink) loginLink.style.display = 'none';
        if (userLink) userLink.style.display = 'flex';
        if (logoutBtn) logoutBtn.style.display = 'flex';
        if (userName) {
            userName.textContent = `您好，${user.name}`;
            userName.style.display = 'inline';
        }

        // 獲取並顯示用戶額度
        try {
            const data = await API.auth.getProfile();
            const credit = (data.user && typeof data.user.credit === 'number') ? data.user.credit : 0;
            displayUserCredit(credit);
        } catch (error) {
            console.error('獲取用戶資料失敗:', error);
            displayUserCredit(0); // Show $0 on error
        }
    } else {
        if (loginLink) loginLink.style.display = 'flex';
        if (userLink) userLink.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'none';
        if (userName) userName.style.display = 'none';

        // 移除額度顯示
        const creditBadge = document.querySelector('.user-credit-badge');
        if (creditBadge) creditBadge.remove();
    }
}

// 顯示用戶額度
function displayUserCredit(credit) {
    // 先移除現有的額度標籤
    const existing = document.querySelector('.user-credit-badge');
    if (existing) existing.remove();

    // 在 user-link 元素後面添加額度顯示
    const userLink = document.querySelector('.user-link');
    if (userLink && credit >= 0) {
        const creditBadge = document.createElement('span');
        creditBadge.className = 'user-credit-badge';
        creditBadge.innerHTML = `
            <i class="fas fa-wallet"></i>
            <span>$${credit.toLocaleString()}</span>
        `;
        creditBadge.style.cssText = `
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 700;
            color: #fff;
            margin-left: 12px;
            box-shadow: 0 2px 8px rgba(255, 152, 0, 0.4);
            text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        `;

        // 如果額度為0，顯示紅色警告樣式
        if (credit === 0) {
            creditBadge.style.background = 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)';
            creditBadge.style.boxShadow = '0 2px 8px rgba(231, 76, 60, 0.4)';
            creditBadge.innerHTML = `
                <i class="fas fa-wallet"></i>
                <span>$0</span>
            `;
        }
        // 插入到 user-link 元素後面
        userLink.insertAdjacentElement('afterend', creditBadge);
    }
}

// 登出
function logout() {
    API.auth.logout();
}

// 搜尋功能
function initSearch() {
    const searchInputs = document.querySelectorAll('.search-box input');
    searchInputs.forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = input.value.trim();
                if (query) {
                    window.location.href = `/frontend/products.html?search=${encodeURIComponent(query)}`;
                }
            }
        });
    });

    const searchBtns = document.querySelectorAll('.search-box button');
    searchBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const input = btn.previousElementSibling;
            const query = input.value.trim();
            if (query) {
                window.location.href = `/frontend/products.html?search=${encodeURIComponent(query)}`;
            }
        });
    });
}

// 頁面載入
document.addEventListener('DOMContentLoaded', () => {
    updateHeaderUI();
    initSearch();

    // 登出按鈕
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
});

// 匯出
window.formatPrice = formatPrice;
window.formatDate = formatDate;
window.getStatusText = getStatusText;
window.showToast = showToast;
window.createProductCard = createProductCard;
window.addToCart = addToCart;
