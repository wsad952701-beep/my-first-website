// 主題載入器 - 從後台讀取並應用主題
async function loadTheme() {
    try {
        const response = await fetch('/api/settings/theme');
        const data = await response.json();
        const theme = data.theme || 'default';

        if (theme !== 'default') {
            document.documentElement.setAttribute('data-theme', theme);
        }

        // 保存到本地以便快速載入
        localStorage.setItem('site_theme', theme);
    } catch (error) {
        // 使用本地緩存的主題
        const cachedTheme = localStorage.getItem('site_theme');
        if (cachedTheme && cachedTheme !== 'default') {
            document.documentElement.setAttribute('data-theme', cachedTheme);
        }
    }
}

// 頁面載入時立即應用緩存主題（避免閃爍）
(function () {
    const cachedTheme = localStorage.getItem('site_theme');
    if (cachedTheme && cachedTheme !== 'default') {
        document.documentElement.setAttribute('data-theme', cachedTheme);
    }
})();

// DOM 載入後確認主題
document.addEventListener('DOMContentLoaded', loadTheme);
