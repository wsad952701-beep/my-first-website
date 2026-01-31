// 主題內容配置 - 根據不同主題顯示不同的活動名稱、類別、標籤等
const themeContent = {
    // 預設主題
    default: {
        name: '預設主題',
        hero: {
            title: '🍇 新鮮水果直送',
            subtitle: '每日嚴選，產地直送到府',
            badge: '限時優惠'
        },
        categories: {
            1: { name: '精選禮盒', icon: '🎁', description: '送禮首選' },
            2: { name: '季節限定', icon: '✨', description: '當季最鮮' },
            3: { name: '進口水果', icon: '🌍', description: '世界美味' },
            4: { name: '日本嚴選', icon: '🇯🇵', description: '頂級品質' },
            5: { name: '台灣在地', icon: '🇹🇼', description: '在地新鮮' },
            6: { name: '優惠專區', icon: '💰', description: '超值優惠' }
        },
        seasonalTabs: ['全部', '當季精選', '熱銷推薦', '新品上市'],
        promoSection: {
            title: '熱門推薦',
            subtitle: '精選人氣商品'
        },
        featuredSection: {
            title: '精選商品',
            subtitle: '嚴選品質保證'
        },
        banner: {
            main: '每日新鮮直送',
            sub: '滿$799免運費'
        }
    },

    // 春天主題
    spring: {
        name: '🌸 春天主題',
        hero: {
            title: '🌸 春日花漾季',
            subtitle: '春暖花開，鮮果飄香',
            badge: '春季特賣'
        },
        categories: {
            1: { name: '春日禮盒', icon: '🌸', description: '春天限定' },
            2: { name: '櫻花季限定', icon: '🌷', description: '粉嫩登場' },
            3: { name: '進口鮮果', icon: '🌍', description: '春季精選' },
            4: { name: '日本春摘', icon: '🇯🇵', description: '春季採收' },
            5: { name: '台灣春果', icon: '🇹🇼', description: '早春滋味' },
            6: { name: '春季特惠', icon: '💐', description: '春天優惠' }
        },
        seasonalTabs: ['全部', '櫻花季', '草莓季', '春果特選'],
        promoSection: {
            title: '🌸 春季限定',
            subtitle: '春暖花開好時節'
        },
        featuredSection: {
            title: '春日精選',
            subtitle: '迎接春天的美味'
        },
        banner: {
            main: '春季新品上市',
            sub: '滿額贈春日好禮'
        }
    },

    // 夏日主題
    summer: {
        name: '🌞 夏日主題',
        hero: {
            title: '🌞 夏日消暑季',
            subtitle: '清涼一夏，鮮果解渴',
            badge: '夏日特賣'
        },
        categories: {
            1: { name: '夏日禮盒', icon: '🏖️', description: '清涼送禮' },
            2: { name: '芒果季限定', icon: '🥭', description: '夏日必吃' },
            3: { name: '熱帶水果', icon: '🌴', description: '消暑聖品' },
            4: { name: '日本夏果', icon: '🇯🇵', description: '夏季限定' },
            5: { name: '台灣夏果', icon: '🇹🇼', description: '在地甜蜜' },
            6: { name: '消暑特惠', icon: '❄️', description: '冰涼優惠' }
        },
        seasonalTabs: ['全部', '芒果季', '荔枝季', '西瓜季'],
        promoSection: {
            title: '🌞 夏日限定',
            subtitle: '消暑解渴好選擇'
        },
        featuredSection: {
            title: '夏日精選',
            subtitle: '清涼一夏的美味'
        },
        banner: {
            main: '夏日水果祭',
            sub: '滿額送冰涼好禮'
        }
    },

    // 秋天主題
    autumn: {
        name: '🍂 秋天主題',
        hero: {
            title: '🍂 秋收豐盈季',
            subtitle: '秋高氣爽，果實飄香',
            badge: '秋季特賣'
        },
        categories: {
            1: { name: '中秋禮盒', icon: '🥮', description: '團圓送禮' },
            2: { name: '柿子季限定', icon: '🍊', description: '秋日甜蜜' },
            3: { name: '進口秋果', icon: '🌍', description: '秋季精選' },
            4: { name: '日本秋摘', icon: '🇯🇵', description: '秋季收穫' },
            5: { name: '台灣秋果', icon: '🇹🇼', description: '秋收時節' },
            6: { name: '秋季特惠', icon: '🍁', description: '楓紅優惠' }
        },
        seasonalTabs: ['全部', '柿子季', '葡萄季', '梨子季'],
        promoSection: {
            title: '🍂 秋季限定',
            subtitle: '豐收時節的美味'
        },
        featuredSection: {
            title: '秋日精選',
            subtitle: '感受秋天的甜蜜'
        },
        banner: {
            main: '秋收感恩季',
            sub: '中秋禮盒特惠中'
        }
    },

    // 冬季主題
    winter: {
        name: '❄️ 冬季主題',
        hero: {
            title: '❄️ 冬日暖心季',
            subtitle: '溫暖冬日，鮮果相伴',
            badge: '冬季特賣'
        },
        categories: {
            1: { name: '聖誕禮盒', icon: '🎄', description: '溫馨送禮' },
            2: { name: '草莓季限定', icon: '🍓', description: '冬日浪漫' },
            3: { name: '進口冬果', icon: '🌍', description: '冬季精選' },
            4: { name: '日本冬摘', icon: '🇯🇵', description: '冬季限定' },
            5: { name: '台灣冬果', icon: '🇹🇼', description: '暖冬滋味' },
            6: { name: '暖冬特惠', icon: '☃️', description: '冬日優惠' }
        },
        seasonalTabs: ['全部', '草莓季', '柑橘季', '蘋果季'],
        promoSection: {
            title: '❄️ 冬季限定',
            subtitle: '溫暖冬日的美味'
        },
        featuredSection: {
            title: '冬日精選',
            subtitle: '暖心好滋味'
        },
        banner: {
            main: '暖冬水果節',
            sub: '聖誕禮盒預購中'
        }
    },

    // 新年主題
    newyear: {
        name: '🧧 新年主題',
        hero: {
            title: '🧧 新春賀歲季',
            subtitle: '金蛇迎春，好運連連',
            badge: '新年特賣'
        },
        categories: {
            1: { name: '新春禮盒', icon: '🧧', description: '拜年首選' },
            2: { name: '年節限定', icon: '🏮', description: '喜氣洋洋' },
            3: { name: '進口鮮果', icon: '🌍', description: '過年必備' },
            4: { name: '日本賀歲', icon: '🇯🇵', description: '頂級送禮' },
            5: { name: '台灣年貨', icon: '🇹🇼', description: '在地好味' },
            6: { name: '新春特惠', icon: '💰', description: '紅包價' }
        },
        seasonalTabs: ['全部', '春節禮盒', '柑橘系列', '開運水果'],
        promoSection: {
            title: '🧧 新春限定',
            subtitle: '金蛇年好禮相送'
        },
        featuredSection: {
            title: '賀歲精選',
            subtitle: '新年送禮首選'
        },
        banner: {
            main: '新春拜年禮',
            sub: '滿額送開運紅包'
        }
    }
};

// 取得當前主題內容
function getThemeContent(themeName) {
    return themeContent[themeName] || themeContent.default;
}

// 應用主題內容到頁面
function applyThemeContent(themeName) {
    const content = getThemeContent(themeName);

    // 更新 Hero 區域第一個標題
    document.querySelectorAll('.hero-slide-content h2').forEach((el, index) => {
        if (index === 0) el.textContent = content.hero.title;
    });

    // 更新分類標題
    document.querySelectorAll('[data-category-id]').forEach(el => {
        const catId = el.dataset.categoryId;
        if (content.categories[catId]) {
            const cat = content.categories[catId];
            const nameEl = el.querySelector('.category-name, h3, .cat-name');
            const iconEl = el.querySelector('.category-icon, .cat-icon');
            const descEl = el.querySelector('.category-desc, .cat-desc');

            if (nameEl) nameEl.textContent = cat.name;
            if (iconEl) iconEl.textContent = cat.icon;
            if (descEl) descEl.textContent = cat.description;
        }
    });

    // 更新精選區域標題
    const featuredTitle = document.getElementById('featured-title');
    const featuredSubtitle = document.getElementById('featured-subtitle');
    if (featuredTitle) {
        featuredTitle.innerHTML = `${content.categories[1].icon} ${content.featuredSection.title} ${content.categories[1].icon}`;
    }
    if (featuredSubtitle) {
        featuredSubtitle.textContent = content.featuredSection.subtitle;
    }

    // 更新季節區域標題
    const seasonalTitle = document.querySelector('.theme-seasonal-title, .seasonal-header h2');
    if (seasonalTitle) {
        seasonalTitle.textContent = `${content.promoSection.title} ${content.promoSection.subtitle}`;
    }

    // 更新季節Tab
    content.seasonalTabs.forEach((tabText, index) => {
        const tab = document.querySelector(`.theme-tab-${index}`) ||
            document.querySelectorAll('.seasonal-tab')[index];
        if (tab) {
            tab.textContent = tabText;
        }
    });

    // 更新頁面標題
    if (window.location.pathname.includes('index.html') || window.location.pathname === '/frontend/') {
        document.title = `${content.name} | 果實搬運工`;
    }

    // 儲存當前主題到localStorage
    localStorage.setItem('site_theme', themeName);
    localStorage.setItem('theme_content', JSON.stringify(content));

    console.log(`主題內容已應用: ${content.name}`);
}

// 載入精選區商品（根據主題選擇分類）
async function loadFeaturedProducts(themeName) {
    const container = document.getElementById('featured-products');
    if (!container) return;

    try {
        // 從API取得分類1的商品（禮盒類）
        const response = await fetch('/api/products?category=1&limit=2');
        const data = await response.json();
        const products = data.products || [];

        if (products.length === 0) {
            container.innerHTML = '<p style="color:rgba(255,255,255,0.5);text-align:center;">暫無商品</p>';
            return;
        }

        let html = '';
        products.forEach(product => {
            // 修正路徑：去除 /frontend/ 前綴
            let imgSrc = product.image_url || 'images/placeholder.png';
            if (imgSrc.startsWith('/frontend/')) {
                imgSrc = imgSrc.replace('/frontend/', '');
            }
            const price = product.price ? `$${product.price.toLocaleString()}` : '';
            const originalPrice = product.original_price ? `$${product.original_price.toLocaleString()}` : '';

            html += `
                <a href="product-detail.html?id=${product.id}" class="cny-card">
                    <div class="cny-card-image">
                        <img src="${imgSrc}" alt="${product.name}">
                    </div>
                    <div class="cny-card-content">
                        <h3>${product.name}</h3>
                        <div>
                            <span class="price">${price}</span>
                            ${originalPrice ? `<span class="original-price">${originalPrice}</span>` : ''}
                        </div>
                    </div>
                </a>
            `;
        });

        // 添加查看全部按鈕
        html += `
            <a href="products.html?category=1" class="cny-card" style="display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05);">
                <div class="cny-card-content">
                    <h3 style="font-size: 1.5rem;">查看全部禮盒 →</h3>
                    <p style="color: rgba(255,255,255,0.7);">更多精選禮盒等你挑選</p>
                </div>
            </a>
        `;

        container.innerHTML = html;
    } catch (error) {
        console.error('載入精選商品失敗:', error);
        container.innerHTML = '<p style="color:rgba(255,255,255,0.5);text-align:center;">載入失敗</p>';
    }
}

// 頁面載入時自動應用主題內容
document.addEventListener('DOMContentLoaded', async function () {
    try {
        // 從API取得當前主題
        const response = await fetch('/api/settings/theme');
        const data = await response.json();
        const themeName = data.theme || 'default';

        // 應用主題內容
        applyThemeContent(themeName);

        // 載入精選區商品
        loadFeaturedProducts(themeName);
    } catch (error) {
        // 使用本地緩存
        const cachedTheme = localStorage.getItem('site_theme') || 'default';
        applyThemeContent(cachedTheme);
        loadFeaturedProducts(cachedTheme);
    }
});

// 導出供其他腳本使用
if (typeof window !== 'undefined') {
    window.themeContent = themeContent;
    window.getThemeContent = getThemeContent;
    window.applyThemeContent = applyThemeContent;
    window.loadFeaturedProducts = loadFeaturedProducts;
}
