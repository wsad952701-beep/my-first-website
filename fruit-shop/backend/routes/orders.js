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

// 歷史購買記錄 (必須在 /:id 之前定義)
router.get('/history/summary', authenticateToken, (req, res) => {
    try {
        // 取得已完成的訂單
        const orders = db.prepare(`
            SELECT o.*, 
                   (SELECT GROUP_CONCAT(oi.name || ' x' || oi.quantity, ', ') 
                    FROM order_items oi WHERE oi.order_id = o.id) as items_summary
            FROM orders o
            WHERE o.user_id = ? AND o.status = 'completed'
            ORDER BY o.created_at DESC
        `).all(req.user.id);

        // 計算總花費
        const totalSpent = orders.reduce((sum, order) => sum + order.total_amount, 0);

        // 取得購買過的商品統計
        const productStats = db.prepare(`
            SELECT oi.name, SUM(oi.quantity) as total_quantity, SUM(oi.unit_price * oi.quantity) as total_spent
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status = 'completed'
            GROUP BY oi.product_id, oi.name
            ORDER BY total_quantity DESC
        `).all(req.user.id);

        res.json({
            orders,
            totalSpent,
            totalOrders: orders.length,
            productStats
        });
    } catch (error) {
        console.error('取得歷史購買記錄錯誤:', error);
        res.status(500).json({ error: '取得歷史購買記錄失敗' });
    }
});

// 刪除所有已完成/已取消的訂單記錄 (必須在 /:id 之前定義)
router.delete('/clear/all', authenticateToken, (req, res) => {
    try {
        // 取得所有可刪除的訂單
        const orders = db.prepare(`
            SELECT id FROM orders 
            WHERE user_id = ? AND status IN ('completed', 'cancelled', 'delivered')
        `).all(req.user.id);

        if (orders.length === 0) {
            return res.json({ message: '沒有可刪除的訂單', deleted: 0 });
        }

        // 刪除訂單項目和訂單
        orders.forEach(order => {
            db.prepare('DELETE FROM order_items WHERE order_id = ?').run(order.id);
            db.prepare('DELETE FROM orders WHERE id = ?').run(order.id);
        });

        res.json({ message: `已刪除 ${orders.length} 筆訂單記錄`, deleted: orders.length });
    } catch (error) {
        console.error('清除訂單錯誤:', error);
        res.status(500).json({ error: '清除訂單失敗' });
    }
});

// 取得訂單詳情 (動態路由必須在特定路由之後)
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

        // 檢查用戶帳號狀態
        const user = db.prepare('SELECT id, status, IFNULL(credit, 0) as credit FROM users WHERE id = ?').get(req.user.id);
        if (!user) {
            return res.status(400).json({ error: '用戶不存在' });
        }

        if (user.status === 'inactive' || user.status === 'suspended') {
            return res.status(403).json({ error: '帳號異常，請聯絡管理員' });
        }

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

        // 檢查會員額度 (user 已在上方查詢過)
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

// 會員取消訂單
router.put('/:id/cancel', authenticateToken, (req, res) => {
    try {
        const { cancel_reason } = req.body;
        const orderId = req.params.id;

        if (!cancel_reason || cancel_reason.trim() === '') {
            return res.status(400).json({ error: '請填寫取消原因' });
        }

        // 確認訂單存在且屬於該會員
        const order = db.prepare(`
            SELECT * FROM orders 
            WHERE id = ? AND user_id = ?
        `).get(orderId, req.user.id);

        if (!order) {
            return res.status(404).json({ error: '訂單不存在' });
        }

        // 只有待處理狀態可以取消
        if (order.status !== 'pending') {
            return res.status(400).json({ error: '只有待處理的訂單可以取消' });
        }

        // 取得訂單項目並恢復庫存
        const orderItems = db.prepare('SELECT * FROM order_items WHERE order_id = ?').all(order.id);
        orderItems.forEach(item => {
            db.prepare('UPDATE products SET stock = stock + ? WHERE id = ?').run(item.quantity, item.product_id);
        });

        // 退還會員額度
        db.prepare('UPDATE users SET credit = credit + ? WHERE id = ?').run(order.total_amount, req.user.id);

        // 更新訂單狀態
        db.prepare('UPDATE orders SET status = ?, cancel_reason = ? WHERE id = ?')
            .run('cancelled', cancel_reason.trim(), orderId);

        res.json({ message: '訂單已取消，額度已退還' });
    } catch (error) {
        console.error('取消訂單錯誤:', error);
        res.status(500).json({ error: '取消訂單失敗' });
    }
});

// 刪除單筆訂單記錄 (只刪除已完成或已取消的訂單)
router.delete('/:id', authenticateToken, (req, res) => {
    try {
        const orderId = req.params.id;

        // 確認訂單存在且屬於該會員
        const order = db.prepare(`
            SELECT * FROM orders 
            WHERE id = ? AND user_id = ?
        `).get(orderId, req.user.id);

        if (!order) {
            return res.status(404).json({ error: '訂單不存在' });
        }

        // 只有已完成或已取消的訂單可以刪除
        if (!['completed', 'cancelled', 'delivered'].includes(order.status)) {
            return res.status(400).json({ error: '只有已完成或已取消的訂單可以刪除' });
        }

        // 刪除訂單項目和訂單
        db.prepare('DELETE FROM order_items WHERE order_id = ?').run(orderId);
        db.prepare('DELETE FROM orders WHERE id = ?').run(orderId);

        res.json({ message: '訂單記錄已刪除' });
    } catch (error) {
        console.error('刪除訂單錯誤:', error);
        res.status(500).json({ error: '刪除訂單失敗' });
    }
});

module.exports = router;
