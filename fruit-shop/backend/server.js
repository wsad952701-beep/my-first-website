const express = require('express');
const cors = require('cors');
const path = require('path');
const { initDatabase } = require('./config/database');

const app = express();
const PORT = process.env.PORT || 3000;

// 中間件
app.use(cors());
app.use(express.json());

// 靜態檔案目錄
app.use('/frontend', express.static(path.join(__dirname, '..', 'frontend')));
app.use('/admin', express.static(path.join(__dirname, '..', 'admin')));
app.use('/images', express.static(path.join(__dirname, '..', 'frontend', 'images')));

// 首頁重定向到前端
app.get('/', (req, res) => {
    res.redirect('/frontend/index.html');
});

// 錯誤處理
app.use((err, req, res, next) => {
    console.error('伺服器錯誤:', err);
    res.status(500).json({ error: '伺服器錯誤' });
});

// 啟動伺服器
async function startServer() {
    try {
        // 初始化資料庫
        await initDatabase();

        // 載入 API 路由 (資料庫初始化後)
        app.use('/api/auth', require('./routes/auth'));
        app.use('/api/products', require('./routes/products'));
        app.use('/api/cart', require('./routes/cart'));
        app.use('/api/orders', require('./routes/orders'));
        app.use('/api/admin', require('./routes/admin'));
        app.use('/api/upload', require('./routes/upload'));

        app.listen(PORT, () => {
            console.log('');
            console.log('🍇 ═══════════════════════════════════════════════════════════');
            console.log('');
            console.log('   🛒 果實搬運工 - 水果電商系統 啟動成功！');
            console.log('');
            console.log(`   📍 前端購物網站: http://localhost:${PORT}/frontend/`);
            console.log(`   📍 後台管理系統: http://localhost:${PORT}/admin/`);
            console.log(`   📍 API 服務:     http://localhost:${PORT}/api/`);
            console.log('');
            console.log('   👤 管理員帳號: admin@fruitporter.com');
            console.log('   🔑 管理員密碼: admin123');
            console.log('');
            console.log('🍇 ═══════════════════════════════════════════════════════════');
            console.log('');
        });
    } catch (error) {
        console.error('啟動失敗:', error);
        process.exit(1);
    }
}

startServer();
