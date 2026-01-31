const express = require('express');
const router = express.Router();
const db = require('../config/database');
const { authenticateToken, requireAdmin } = require('../middleware/auth');

// 取得網站設定
router.get('/', (req, res) => {
    try {
        const settings = db.prepare('SELECT * FROM settings').all();
        const settingsObj = {};
        settings.forEach(s => {
            settingsObj[s.key] = s.value;
        });
        res.json({ settings: settingsObj });
    } catch (error) {
        console.error('取得設定錯誤:', error);
        res.status(500).json({ error: '取得設定失敗' });
    }
});

// 取得當前主題
router.get('/theme', (req, res) => {
    try {
        const theme = db.prepare('SELECT value FROM settings WHERE key = ?').get('current_theme');
        res.json({ theme: theme ? theme.value : 'default' });
    } catch (error) {
        console.error('取得主題錯誤:', error);
        res.status(500).json({ error: '取得主題失敗' });
    }
});

// 更新主題 (需管理員權限)
router.put('/theme', authenticateToken, requireAdmin, (req, res) => {
    try {
        const { theme } = req.body;

        // 預定義的主題列表
        const validThemes = ['default', 'spring', 'summer', 'autumn', 'winter', 'newyear'];

        if (!theme || !validThemes.includes(theme)) {
            return res.status(400).json({
                error: '無效的主題',
                validThemes
            });
        }

        // 更新或插入設定
        const existing = db.prepare('SELECT id FROM settings WHERE key = ?').get('current_theme');

        if (existing) {
            db.prepare('UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?')
                .run(theme, 'current_theme');
        } else {
            db.prepare('INSERT INTO settings (key, value) VALUES (?, ?)')
                .run('current_theme', theme);
        }

        res.json({ message: '主題更新成功', theme });
    } catch (error) {
        console.error('更新主題錯誤:', error);
        res.status(500).json({ error: '更新主題失敗' });
    }
});

// 取得可用主題列表
router.get('/themes', (req, res) => {
    const themes = [
        { id: 'default', name: '預設主題', description: '經典深色主題', colors: ['#0d1117', '#f4a261', '#e9c46a'] },
        { id: 'spring', name: '🌸 春天主題', description: '粉嫩櫻花風格', colors: ['#1a1a2e', '#ffb3c1', '#ff758f'] },
        { id: 'summer', name: '🌞 夏日主題', description: '清新海洋風格', colors: ['#1a3d5c', '#00d4ff', '#48cae4'] },
        { id: 'autumn', name: '🍂 秋天主題', description: '溫暖楓葉風格', colors: ['#2d1b00', '#ff9f1c', '#ffbf69'] },
        { id: 'winter', name: '❄️ 冬季主題', description: '冰雪純淨風格', colors: ['#0a1628', '#a8dadc', '#457b9d'] },
        { id: 'newyear', name: '🧧 新年主題', description: '喜氣洋洋紅金風格', colors: ['#1a0a0a', '#dc2626', '#fbbf24'] }
    ];

    res.json({ themes });
});

// 取得跑馬燈文字
router.get('/marquee', (req, res) => {
    try {
        const marquee = db.prepare('SELECT value FROM settings WHERE key = ?').get('marquee_text');
        res.json({
            marquee: marquee ? marquee.value : '🎉 歡迎光臨果實搬運工！新年特惠活動進行中 🧧 滿$799免運費 🍇 每日新鮮直送'
        });
    } catch (error) {
        console.error('取得跑馬燈錯誤:', error);
        res.status(500).json({ error: '取得跑馬燈失敗' });
    }
});

// 更新跑馬燈文字 (需管理員權限)
router.put('/marquee', authenticateToken, requireAdmin, (req, res) => {
    try {
        const { marquee } = req.body;

        if (typeof marquee !== 'string') {
            return res.status(400).json({ error: '跑馬燈內容無效' });
        }

        // 更新或插入設定
        const existing = db.prepare('SELECT id FROM settings WHERE key = ?').get('marquee_text');

        if (existing) {
            db.prepare('UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?')
                .run(marquee, 'marquee_text');
        } else {
            db.prepare('INSERT INTO settings (key, value) VALUES (?, ?)')
                .run('marquee_text', marquee);
        }

        res.json({ message: '跑馬燈更新成功', marquee });
    } catch (error) {
        console.error('更新跑馬燈錯誤:', error);
        res.status(500).json({ error: '更新跑馬燈失敗' });
    }
});

module.exports = router;
