const express = require('express');
const router = express.Router();
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');

// 取得收藏列表
router.get('/', authenticateToken, (req, res) => {
    try {
        const favorites = db.prepare(`
            SELECT f.id, f.product_id, f.created_at,
                   p.name, p.price, p.original_price, p.image_url, p.stock,
                   p.is_featured, p.is_seasonal,
                   c.name as category_name
            FROM favorites f
            JOIN products p ON f.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE f.user_id = ?
            ORDER BY f.created_at DESC
        `).all(req.user.id);

        res.json({ favorites });
    } catch (error) {
        console.error('取得收藏列表錯誤:', error);
        res.status(500).json({ error: '取得收藏列表失敗' });
    }
});

// 檢查商品是否已收藏
router.get('/check/:productId', authenticateToken, (req, res) => {
    try {
        const favorite = db.prepare(`
            SELECT id FROM favorites 
            WHERE user_id = ? AND product_id = ?
        `).get(req.user.id, req.params.productId);

        res.json({ isFavorite: !!favorite });
    } catch (error) {
        console.error('檢查收藏狀態錯誤:', error);
        res.status(500).json({ error: '檢查收藏狀態失敗' });
    }
});

// 新增收藏
router.post('/', authenticateToken, (req, res) => {
    try {
        const { product_id } = req.body;

        if (!product_id) {
            return res.status(400).json({ error: '請指定商品' });
        }

        // 檢查商品是否存在
        const product = db.prepare('SELECT id FROM products WHERE id = ?').get(product_id);
        if (!product) {
            return res.status(404).json({ error: '商品不存在' });
        }

        // 檢查是否已收藏
        const existing = db.prepare(`
            SELECT id FROM favorites 
            WHERE user_id = ? AND product_id = ?
        `).get(req.user.id, product_id);

        if (existing) {
            return res.status(400).json({ error: '商品已在收藏中' });
        }

        // 新增收藏
        db.prepare(`
            INSERT INTO favorites (user_id, product_id)
            VALUES (?, ?)
        `).run(req.user.id, product_id);

        res.status(201).json({ message: '已加入收藏' });
    } catch (error) {
        console.error('新增收藏錯誤:', error);
        res.status(500).json({ error: '新增收藏失敗' });
    }
});

// 移除收藏
router.delete('/:productId', authenticateToken, (req, res) => {
    try {
        const result = db.prepare(`
            DELETE FROM favorites 
            WHERE user_id = ? AND product_id = ?
        `).run(req.user.id, req.params.productId);

        if (result.changes === 0) {
            return res.status(404).json({ error: '收藏不存在' });
        }

        res.json({ message: '已移除收藏' });
    } catch (error) {
        console.error('移除收藏錯誤:', error);
        res.status(500).json({ error: '移除收藏失敗' });
    }
});

// 切換收藏狀態
router.post('/toggle', authenticateToken, (req, res) => {
    try {
        const { product_id } = req.body;

        if (!product_id) {
            return res.status(400).json({ error: '請指定商品' });
        }

        // 檢查是否已收藏
        const existing = db.prepare(`
            SELECT id FROM favorites 
            WHERE user_id = ? AND product_id = ?
        `).get(req.user.id, product_id);

        if (existing) {
            // 移除收藏
            db.prepare(`DELETE FROM favorites WHERE id = ?`).run(existing.id);
            res.json({ message: '已移除收藏', isFavorite: false });
        } else {
            // 新增收藏
            db.prepare(`
                INSERT INTO favorites (user_id, product_id)
                VALUES (?, ?)
            `).run(req.user.id, product_id);
            res.json({ message: '已加入收藏', isFavorite: true });
        }
    } catch (error) {
        console.error('切換收藏狀態錯誤:', error);
        res.status(500).json({ error: '操作失敗' });
    }
});

module.exports = router;
