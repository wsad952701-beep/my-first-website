const express = require('express');
const router = express.Router();
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');

// 取得購物車
router.get('/', authenticateToken, (req, res) => {
    try {
        const items = db.prepare(`
            SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.image_url, p.stock
            FROM cart_items c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        `).all(req.user.id);

        const total = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);

        res.json({ items, total });
    } catch (error) {
        console.error('取得購物車錯誤:', error);
        res.status(500).json({ error: '取得購物車失敗' });
    }
});

// 加入購物車
router.post('/', authenticateToken, (req, res) => {
    try {
        const { product_id, quantity = 1 } = req.body;

        if (!product_id) {
            return res.status(400).json({ error: '請指定產品' });
        }

        // 檢查產品是否存在
        const product = db.prepare('SELECT * FROM products WHERE id = ?').get(product_id);
        if (!product) {
            return res.status(404).json({ error: '產品不存在' });
        }

        // 檢查庫存
        if (product.stock < quantity) {
            return res.status(400).json({ error: '庫存不足' });
        }

        // 檢查是否已在購物車中
        const existing = db.prepare(
            'SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?'
        ).get(req.user.id, product_id);

        if (existing) {
            // 更新數量
            const newQuantity = existing.quantity + quantity;
            if (product.stock < newQuantity) {
                return res.status(400).json({ error: '庫存不足' });
            }
            db.prepare('UPDATE cart_items SET quantity = ? WHERE id = ?').run(newQuantity, existing.id);
        } else {
            // 新增到購物車
            db.prepare(
                'INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)'
            ).run(req.user.id, product_id, quantity);
        }

        // 取得更新後的購物車
        const items = db.prepare(`
            SELECT c.id, c.quantity, p.id as product_id, p.name, p.price, p.image_url
            FROM cart_items c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        `).all(req.user.id);

        res.json({ message: '已加入購物車', items });
    } catch (error) {
        console.error('加入購物車錯誤:', error);
        res.status(500).json({ error: '加入購物車失敗' });
    }
});

// 更新購物車數量
router.put('/:id', authenticateToken, (req, res) => {
    try {
        const { quantity } = req.body;

        if (!quantity || quantity < 1) {
            return res.status(400).json({ error: '數量必須大於 0' });
        }

        // 檢查購物車項目
        const cartItem = db.prepare(
            'SELECT c.*, p.stock FROM cart_items c JOIN products p ON c.product_id = p.id WHERE c.id = ? AND c.user_id = ?'
        ).get(req.params.id, req.user.id);

        if (!cartItem) {
            return res.status(404).json({ error: '購物車項目不存在' });
        }

        if (cartItem.stock < quantity) {
            return res.status(400).json({ error: '庫存不足' });
        }

        db.prepare('UPDATE cart_items SET quantity = ? WHERE id = ?').run(quantity, req.params.id);

        res.json({ message: '更新成功' });
    } catch (error) {
        console.error('更新購物車錯誤:', error);
        res.status(500).json({ error: '更新購物車失敗' });
    }
});

// 移除購物車項目
router.delete('/:id', authenticateToken, (req, res) => {
    try {
        // 先檢查項目是否存在
        const item = db.prepare('SELECT id FROM cart_items WHERE id = ? AND user_id = ?').get(req.params.id, req.user.id);
        if (!item) {
            return res.status(404).json({ error: '購物車項目不存在' });
        }

        db.prepare('DELETE FROM cart_items WHERE id = ? AND user_id = ?').run(req.params.id, req.user.id);

        res.json({ message: '已從購物車移除' });
    } catch (error) {
        console.error('移除購物車錯誤:', error);
        res.status(500).json({ error: '移除失敗' });
    }
});

// 清空購物車
router.delete('/', authenticateToken, (req, res) => {
    try {
        db.prepare('DELETE FROM cart_items WHERE user_id = ?').run(req.user.id);
        res.json({ message: '購物車已清空' });
    } catch (error) {
        console.error('清空購物車錯誤:', error);
        res.status(500).json({ error: '清空購物車失敗' });
    }
});

module.exports = router;
