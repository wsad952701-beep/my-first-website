const express = require('express');
const router = express.Router();
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');

// 產生訂單編號
function generateOrderNumber() {
    const date = new Date();
    const year = date.getFullYear().toString().slice(-2);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const random = Math.random().toString(36).substring(2, 8).toUpperCase();
    return `FP${year}${month}${day}${random}`;
}

// 取得會員訂單列表
router.get('/', authenticateToken, (req, res) => {
    try {
        const orders = db.prepare(`
            SELECT * FROM orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        `).all(req.user.id);

        res.json({ orders });
    } catch (error) {
        console.error('取得訂單錯誤:', error);
        res.status(500).json({ error: '取得訂單失敗' });
    }
});

// 取得訂單詳情
router.get('/:id', authenticateToken, (req, res) => {
    try {
        const order = db.prepare(`
            SELECT * FROM orders 
            WHERE id = ? AND user_id = ?
        `).get(req.params.id, req.user.id);

        if (!order) {
            return res.status(404).json({ error: '訂單不存在' });
        }

        // 取得訂單項目
        const items = db.prepare(`
            SELECT oi.*, p.image_url
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        `).all(order.id);

        res.json({ order, items });
    } catch (error) {
        console.error('取得訂單詳情錯誤:', error);
        res.status(500).json({ error: '取得訂單詳情失敗' });
    }
});

// 建立訂單
router.post('/', authenticateToken, (req, res) => {
    try {
        const { shipping_name, shipping_phone, shipping_address, notes } = req.body;

        if (!shipping_name || !shipping_phone || !shipping_address) {
            return res.status(400).json({ error: '請填寫完整的收件資訊' });
        }

        // 取得購物車 (使用正確的表名 cart_items)
        const cartItems = db.prepare(`
            SELECT c.*, p.price, p.stock, p.name
            FROM cart_items c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        `).all(req.user.id);

        if (cartItems.length === 0) {
            return res.status(400).json({ error: '購物車是空的' });
        }

        // 檢查庫存
        for (const item of cartItems) {
            if (item.stock < item.quantity) {
                return res.status(400).json({ error: `${item.name} 庫存不足` });
            }
        }

        // 計算總金額
        const subtotal = cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const shipping = subtotal >= 799 ? 0 : 100;
        const totalAmount = subtotal + shipping;

        // 檢查會員額度
        const user = db.prepare('SELECT id, IFNULL(credit, 0) as credit FROM users WHERE id = ?').get(req.user.id);
        if (!user) {
            return res.status(400).json({ error: '用戶不存在' });
        }

        if (user.credit < totalAmount) {
            return res.status(400).json({ error: '額度不足，請聯絡管理人員' });
        }

        // 建立訂單
        const orderNumber = generateOrderNumber();
        db.prepare(`
            INSERT INTO orders (user_id, order_number, total_amount, shipping_name, shipping_phone, shipping_address, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        `).run(
            req.user.id,
            orderNumber,
            totalAmount,
            shipping_name,
            shipping_phone,
            shipping_address,
            notes || null
        );

        // 用 order_number 查詢剛建的訂單
        const newOrder = db.prepare('SELECT * FROM orders WHERE order_number = ?').get(orderNumber);
        const orderId = newOrder.id;

        // 建立訂單項目並更新庫存
        for (const item of cartItems) {
            db.prepare(`
                INSERT INTO order_items (order_id, product_id, name, quantity, unit_price)
                VALUES (?, ?, ?, ?, ?)
            `).run(orderId, item.product_id, item.name, item.quantity, item.price);

            db.prepare('UPDATE products SET stock = stock - ? WHERE id = ?').run(item.quantity, item.product_id);
        }

        // 扣除會員額度
        db.prepare('UPDATE users SET credit = credit - ? WHERE id = ?').run(totalAmount, req.user.id);

        // 清空購物車 (使用正確的表名 cart_items)
        db.prepare('DELETE FROM cart_items WHERE user_id = ?').run(req.user.id);

        res.status(201).json({
            message: '訂單建立成功',
            order: {
                id: orderId,
                order_number: orderNumber,
                total_amount: totalAmount
            }
        });
    } catch (error) {
        console.error('建立訂單錯誤:', error);
        res.status(500).json({ error: '建立訂單失敗' });
    }
});

module.exports = router;
