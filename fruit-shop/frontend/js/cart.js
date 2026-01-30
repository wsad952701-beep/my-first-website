// 購物車管理
const cart = {
    items: [],
    total: 0,

    async fetch() {
        if (!TokenManager.isLoggedIn()) {
            this.items = [];
            this.total = 0;
            this.updateUI();
            return;
        }

        try {
            const data = await API.cart.get();
            this.items = data.items || [];
            this.total = data.total || 0;
            this.updateUI();
        } catch (error) {
            console.error('取得購物車失敗:', error);
        }
    },

    updateUI() {
        const cartCount = document.querySelector('.cart-count');
        if (cartCount) {
            const totalItems = this.items.reduce((sum, item) => sum + item.quantity, 0);
            cartCount.textContent = totalItems;
            cartCount.style.display = totalItems > 0 ? 'block' : 'none';
        }
    }
};

// 頁面載入時取得購物車
document.addEventListener('DOMContentLoaded', () => {
    cart.fetch();
});

// 匯出
window.cart = cart;
