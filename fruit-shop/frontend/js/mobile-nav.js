/**
 * 果實搬運工 - 手機版導航組件
 * 自動注入底部導航和漢堡選單功能
 */

(function () {
    'use strict';

    // 底部導航 HTML
    const bottomNavHTML = `
    <nav class="mobile-bottom-nav" id="mobileBottomNav">
        <div class="mobile-bottom-nav-content">
            <a href="index.html" class="mobile-nav-item" data-page="index">
                <i class="fas fa-home"></i>
                <span>首頁</span>
            </a>
            <a href="products.html" class="mobile-nav-item" data-page="products">
                <i class="fas fa-store"></i>
                <span>商品</span>
            </a>
            <a href="cart.html" class="mobile-nav-item" data-page="cart">
                <i class="fas fa-shopping-cart"></i>
                <span>購物車</span>
                <span class="cart-badge" id="mobileCartBadge" style="display:none;">0</span>
            </a>
            <a href="favorites.html" class="mobile-nav-item" data-page="favorites">
                <i class="fas fa-heart"></i>
                <span>收藏</span>
            </a>
            <a href="orders.html" class="mobile-nav-item" data-page="orders">
                <i class="fas fa-user"></i>
                <span>會員</span>
            </a>
        </div>
    </nav>`;

    // 漢堡選單 HTML
    const hamburgerHTML = `
    <div class="mobile-menu-toggle" id="mobileMenuToggle">
        <span></span>
        <span></span>
        <span></span>
    </div>`;

    // 當 DOM 載入完成時執行
    document.addEventListener('DOMContentLoaded', function () {
        // 1. 注入漢堡選單到 header-actions
        const headerActions = document.querySelector('.header-actions');
        if (headerActions && !document.getElementById('mobileMenuToggle')) {
            headerActions.insertAdjacentHTML('afterbegin', hamburgerHTML);
        }

        // 2. 注入底部導航到 body 最後
        if (!document.getElementById('mobileBottomNav')) {
            document.body.insertAdjacentHTML('beforeend', bottomNavHTML);
        }

        // 3. 設置當前頁面的 active 狀態
        setActiveNavItem();

        // 4. 初始化漢堡選單功能
        initHamburgerMenu();

        // 5. 同步購物車數量
        initCartBadgeSync();

        // 6. 檢查是否為認證頁面
        checkAuthPage();
    });

    // 設置當前頁面的 active 狀態
    function setActiveNavItem() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const pageMapping = {
            'index.html': 'index',
            '': 'index',
            'products.html': 'products',
            'product-detail.html': 'products',
            'cart.html': 'cart',
            'checkout.html': 'cart',
            'favorites.html': 'favorites',
            'orders.html': 'orders',
            'history.html': 'orders',
            'login.html': 'orders',
            'register.html': 'orders'
        };

        const activePage = pageMapping[currentPage] || 'index';

        document.querySelectorAll('.mobile-nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.page === activePage) {
                item.classList.add('active');
            }
        });
    }

    // 初始化漢堡選單
    function initHamburgerMenu() {
        const toggle = document.getElementById('mobileMenuToggle');
        const nav = document.querySelector('.nav');

        if (toggle && nav) {
            toggle.addEventListener('click', function () {
                this.classList.toggle('active');
                nav.classList.toggle('mobile-open');
                document.body.style.overflow = nav.classList.contains('mobile-open') ? 'hidden' : '';
            });

            // 點擊導航連結後關閉選單
            nav.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', function () {
                    toggle.classList.remove('active');
                    nav.classList.remove('mobile-open');
                    document.body.style.overflow = '';
                });
            });
        }
    }

    // 同步購物車數量到手機底部導航
    function initCartBadgeSync() {
        function updateMobileCartBadge() {
            const cartCount = document.querySelector('.cart-count');
            const mobileCartBadge = document.getElementById('mobileCartBadge');
            if (cartCount && mobileCartBadge) {
                const count = parseInt(cartCount.textContent) || 0;
                mobileCartBadge.textContent = count;
                mobileCartBadge.style.display = count > 0 ? 'block' : 'none';
            }
        }

        // 初始更新
        updateMobileCartBadge();

        // 監聽購物車變化
        const cartCountEl = document.querySelector('.cart-count');
        if (cartCountEl) {
            const observer = new MutationObserver(updateMobileCartBadge);
            observer.observe(cartCountEl, { childList: true, characterData: true, subtree: true });
        }

        // 每秒檢查一次（備用）
        setInterval(updateMobileCartBadge, 1000);
    }

    // 檢查是否為認證頁面（隱藏底部導航）
    function checkAuthPage() {
        const currentPage = window.location.pathname.split('/').pop();
        const authPages = ['login.html', 'register.html'];

        if (authPages.includes(currentPage)) {
            document.body.classList.add('auth-page');
        }
    }

    // 暴露給全局使用
    window.MobileNav = {
        refresh: function () {
            setActiveNavItem();
        },
        updateCartBadge: function (count) {
            const badge = document.getElementById('mobileCartBadge');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'block' : 'none';
            }
        }
    };
})();
