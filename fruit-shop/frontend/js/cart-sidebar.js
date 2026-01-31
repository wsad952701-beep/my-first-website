// 購物車側邊欄功能

// 創建側邊欄HTML
function createCartSidebar() {
    // 檢查是否已存在
    if (document.getElementById('cart-sidebar')) return;

    const html = `
        <div class="cart-sidebar-overlay" id="cart-sidebar-overlay"></div>
        <div class="cart-sidebar" id="cart-sidebar">
            <div class="cart-sidebar-header">
                <h3><i class="fas fa-shopping-cart"></i> 購物車</h3>
                <button class="cart-sidebar-close" onclick="closeCartSidebar()">&times;</button>
            </div>
            <div class="cart-sidebar-shipping" id="cart-sidebar-shipping"></div>
            <div class="cart-sidebar-items" id="cart-sidebar-items">
                <div class="cart-sidebar-empty">
                    <i class="fas fa-shopping-cart"></i>
                    <p>購物車是空的</p>
                </div>
            </div>
            <div class="cart-sidebar-footer" id="cart-sidebar-footer" style="display:none;">
                <div class="cart-sidebar-total">
                    <span>商品總計</span>
                    <span id="cart-sidebar-total-price">$0</span>
                </div>
                <div class="cart-sidebar-buttons">
                    <a href="/frontend/cart.html" class="btn btn-view">
                        <i class="fas fa-shopping-cart"></i> 查看購物車
                    </a>
                    <a href="/frontend/checkout.html" class="btn btn-checkout">
                        <i class="fas fa-credit-card"></i> 結帳
                    </a>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', html);

    // 點擊遮罩關閉
    document.getElementById('cart-sidebar-overlay').addEventListener('click', closeCartSidebar);
}

// 開啟側邊欄
async function openCartSidebar() {
    createCartSidebar();

    document.getElementById('cart-sidebar').classList.add('active');
    document.getElementById('cart-sidebar-overlay').classList.add('active');
    document.body.style.overflow = 'hidden';

    // 載入購物車內容
    await loadCartSidebarItems();
}

// 關閉側邊欄
function closeCartSidebar() {
    const sidebar = document.getElementById('cart-sidebar');
    const overlay = document.getElementById('cart-sidebar-overlay');

    if (sidebar) sidebar.classList.remove('active');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
}

// 載入購物車商品
async function loadCartSidebarItems() {
    const itemsContainer = document.getElementById('cart-sidebar-items');
    const footerContainer = document.getElementById('cart-sidebar-footer');
    const shippingContainer = document.getElementById('cart-sidebar-shipping');

    if (!TokenManager.isLoggedIn()) {
        itemsContainer.innerHTML = `
            <div class="cart-sidebar-empty">
                <i class="fas fa-user-lock"></i>
                <p>請先登入會員</p>
                <a href="/frontend/login.html" class="btn btn-primary" style="margin-top:15px;padding:8px 20px;border-radius:8px;background:var(--theme-accent);color:#000;text-decoration:none;">
                    前往登入
                </a>
            </div>
        `;
        shippingContainer.style.display = 'none';
        footerContainer.style.display = 'none';
        return;
    }

    try {
        const { items, total } = await API.cart.get();

        if (!items || items.length === 0) {
            itemsContainer.innerHTML = `
                <div class="cart-sidebar-empty">
                    <i class="fas fa-shopping-cart"></i>
                    <p>購物車是空的</p>
                    <a href="/frontend/products.html" class="btn btn-primary" style="margin-top:15px;padding:8px 20px;border-radius:8px;background:var(--theme-accent);color:#000;text-decoration:none;">
                        開始購物
                    </a>
                </div>
            `;
            shippingContainer.style.display = 'none';
            footerContainer.style.display = 'none';
            return;
        }

        // 免運門檻提示
        const freeShippingThreshold = 799;
        if (total >= freeShippingThreshold) {
            shippingContainer.innerHTML = `<p><span class="success">✓ 恭喜！您已享有免運優惠</span></p>`;
            shippingContainer.classList.remove('need-more');
        } else {
            const remaining = freeShippingThreshold - total;
            shippingContainer.innerHTML = `<p><i class="fas fa-truck"></i> 再買 <span class="highlight">$${remaining.toLocaleString()}</span> 即可享免運！</p>`;
            shippingContainer.classList.add('need-more');
        }
        shippingContainer.style.display = 'block';

        // 渲染商品
        itemsContainer.innerHTML = items.map(item => `
            <div class="cart-sidebar-item" data-id="${item.id}">
                <div class="cart-sidebar-item-image">
                    ${item.image_url ?
                `<img src="${item.image_url}" alt="${item.name}" onerror="this.parentElement.innerHTML='🍎'">` :
                '<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:1.5rem;">🍎</div>'
            }
                </div>
                <div class="cart-sidebar-item-info">
                    <div class="cart-sidebar-item-name">${item.name}</div>
                    <div class="cart-sidebar-item-price">$${(item.price * item.quantity).toLocaleString()}</div>
                    <div class="cart-sidebar-item-qty">
                        <button onclick="updateSidebarItem(${item.id}, ${item.quantity - 1})">-</button>
                        <span>${item.quantity}</span>
                        <button onclick="updateSidebarItem(${item.id}, ${item.quantity + 1})">+</button>
                    </div>
                </div>
                <button class="cart-sidebar-item-remove" onclick="removeSidebarItem(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');

        // 更新總價
        document.getElementById('cart-sidebar-total-price').textContent = `$${total.toLocaleString()}`;
        footerContainer.style.display = 'block';

    } catch (error) {
        console.error('載入購物車失敗:', error);
        itemsContainer.innerHTML = `<p style="color:#e74c3c;text-align:center;padding:20px;">載入失敗</p>`;
    }
}

// 更新側邊欄商品數量
async function updateSidebarItem(itemId, quantity) {
    if (quantity < 1) {
        removeSidebarItem(itemId);
        return;
    }

    try {
        await API.cart.update(itemId, quantity);
        await loadCartSidebarItems();
        if (typeof updateCartCount === 'function') {
            updateCartCount();
        }
    } catch (error) {
        console.error('更新失敗:', error);
    }
}

// 移除側邊欄商品
async function removeSidebarItem(itemId) {
    try {
        await API.cart.remove(itemId);
        await loadCartSidebarItems();
        if (typeof updateCartCount === 'function') {
            updateCartCount();
        }
    } catch (error) {
        console.error('移除失敗:', error);
    }
}

// 綁定購物車圖示點擊事件
document.addEventListener('DOMContentLoaded', function () {
    // 攔截購物車連結點擊
    document.querySelectorAll('.cart-icon, a[href*="cart.html"]').forEach(el => {
        // 只攔截header中的購物車圖示，不攔截導航連結
        if (el.classList.contains('cart-icon') || el.closest('.header-actions')) {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                openCartSidebar();
            });
        }
    });
});
