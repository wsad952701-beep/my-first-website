const express = require('express');
const router = express.Router();
const db = require('../config/database');
const { authenticateToken, requireAdmin } = require('../middleware/auth');

// 所有管理員路由都需要驗證
router.use(authenticateToken);
router.use(requireAdmin);

// 儀表板數據
router.get('/dashboard', (req, res) => {
    try {
        // 今日日期
        const today = new Date().toISOString().split('T')[0];

        // 今日訂單統計
        const todayStats = db.prepare(`
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total_amount), 0) as total_revenue
            FROM orders 
            WHERE DATE(created_at) = DATE(?)
        `).get(today);

        // 總營收和總訂單統計
        const totalStats = db.prepare(`
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total_amount), 0) as total_revenue
            FROM orders
        `).get();

        // 總會員數
        const memberCount = db.prepare(`
            SELECT COUNT(*) as count FROM users WHERE is_admin = 0
        `).get();

        // 總產品數
        const productCount = db.prepare(`
            SELECT COUNT(*) as count FROM products
        `).get();

        // 待處理訂單
        const pendingOrders = db.prepare(`
            SELECT COUNT(*) as count FROM orders WHERE status = 'pending'
        `).get();

        // 近7天銷售趨勢
        const salesTrend = db.prepare(`
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as order_count,
                SUM(total_amount) as revenue
            FROM orders 
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        `).all();

        // 最近10筆訂單
        const recentOrders = db.prepare(`
            SELECT o.*, u.name as customer_name, u.email as customer_email
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 10
        `).all();

        // 熱門產品
        const topProducts = db.prepare(`
            SELECT 
                p.id, p.name, p.price, p.image_url,
                SUM(oi.quantity) as total_sold
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            GROUP BY p.id
            ORDER BY total_sold DESC
            LIMIT 5
        `).all();

        res.json({
            today: {
                orders: todayStats.order_count,
                revenue: todayStats.total_revenue
            },
            total: {
                members: memberCount.count,
                products: productCount.count,
                pending_orders: pendingOrders.count,
                orders: totalStats.order_count,
                revenue: totalStats.total_revenue
            },
            salesTrend,
            recentOrders,
            topProducts
        });
    } catch (error) {
        console.error('取得儀表板數據錯誤:', error);
        res.status(500).json({ error: '取得數據失敗' });
    }
});

// 取得所有訂單
router.get('/orders', (req, res) => {
    try {
        const { status, search, limit = 50, offset = 0 } = req.query;

        let sql = `
            SELECT o.*, u.name as customer_name, u.email as customer_email
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE 1=1
        `;
        const params = [];

        if (status) {
            sql += ' AND o.status = ?';
            params.push(status);
        }

        if (search) {
            sql += ' AND (o.order_number LIKE ? OR u.name LIKE ? OR u.email LIKE ?)';
            params.push(`%${search}%`, `%${search}%`, `%${search}%`);
        }

        sql += ' ORDER BY o.created_at DESC LIMIT ? OFFSET ?';
        params.push(parseInt(limit), parseInt(offset));

        const orders = db.prepare(sql).all(...params);

        // 取得總數
        let countSql = `
            SELECT COUNT(*) as total
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE 1=1
        `;
        const countParams = [];
        if (status) {
            countSql += ' AND o.status = ?';
            countParams.push(status);
        }
        if (search) {
            countSql += ' AND (o.order_number LIKE ? OR u.name LIKE ? OR u.email LIKE ?)';
            countParams.push(`%${search}%`, `%${search}%`, `%${search}%`);
        }
        const total = db.prepare(countSql).get(...countParams);

        res.json({ orders, total: total.total });
    } catch (error) {
        console.error('取得訂單錯誤:', error);
        res.status(500).json({ error: '取得訂單失敗' });
    }
});

// 取得訂單詳情
router.get('/orders/:id', (req, res) => {
    try {
        const order = db.prepare(`
            SELECT o.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        `).get(req.params.id);

        if (!order) {
            return res.status(404).json({ error: '訂單不存在' });
        }

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

// 更新訂單狀態
router.put('/orders/:id/status', (req, res) => {
    try {
        const { status, cancel_reason, admin_note } = req.body;
        const validStatuses = ['pending', 'processing', 'shipped', 'completed', 'cancelled'];

        if (!validStatuses.includes(status)) {
            return res.status(400).json({ error: '無效的訂單狀態' });
        }

        // 先確認訂單存在並取得訂單資料
        const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(req.params.id);
        if (!order) {
            return res.status(404).json({ error: '訂單不存在' });
        }

        // 如果是取消訂單，需要處理退款和庫存
        if (status === 'cancelled' && order.status !== 'cancelled') {
            // 取得訂單項目
            const orderItems = db.prepare('SELECT * FROM order_items WHERE order_id = ?').all(order.id);

            // 恢復庫存
            orderItems.forEach(item => {
                db.prepare('UPDATE products SET stock = stock + ? WHERE id = ?').run(item.quantity, item.product_id);
            });

            // 退還會員額度
            db.prepare('UPDATE users SET credit = credit + ? WHERE id = ?').run(order.total_amount, order.user_id);
        }

        // 更新訂單狀態
        if (status === 'cancelled') {
            db.prepare('UPDATE orders SET status = ?, cancel_reason = ?, admin_note = ? WHERE id = ?')
                .run(status, cancel_reason || null, admin_note || null, req.params.id);
        } else {
            db.prepare('UPDATE orders SET status = ? WHERE id = ?').run(status, req.params.id);
        }

        res.json({ message: '訂單狀態已更新' });
    } catch (error) {
        console.error('更新訂單狀態錯誤:', error);
        res.status(500).json({ error: '更新失敗' });
    }
});

// 取得所有產品 (管理用)
router.get('/products', (req, res) => {
    try {
        const products = db.prepare(`
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.id DESC
        `).all();

        res.json({ products });
    } catch (error) {
        console.error('取得產品錯誤:', error);
        res.status(500).json({ error: '取得產品失敗' });
    }
});

// 新增產品
router.post('/products', (req, res) => {
    try {
        const { category_id, name, description, price, original_price, image_url, stock, is_featured, is_seasonal } = req.body;

        if (!name || !price) {
            return res.status(400).json({ error: '請填寫產品名稱和價格' });
        }

        db.prepare(`
            INSERT INTO products (category_id, name, description, price, original_price, image_url, stock, is_featured, is_seasonal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).run(
            category_id || null,
            name,
            description || null,
            price,
            original_price || null,
            image_url || null,
            stock || 0,
            is_featured ? 1 : 0,
            is_seasonal ? 1 : 0
        );

        // 用 name 查詢剛建的產品（按 ID 降序取最新一筆）
        const product = db.prepare('SELECT * FROM products WHERE name = ? ORDER BY id DESC LIMIT 1').get(name);
        res.status(201).json({ message: '產品已新增', product });
    } catch (error) {
        console.error('新增產品錯誤:', error);
        res.status(500).json({ error: '新增產品失敗' });
    }
});

// 更新產品
router.put('/products/:id', (req, res) => {
    try {
        const { category_id, name, description, price, original_price, image_url, stock, is_featured, is_seasonal } = req.body;

        // 先確認產品存在
        const existing = db.prepare('SELECT id FROM products WHERE id = ?').get(req.params.id);
        if (!existing) {
            return res.status(404).json({ error: '產品不存在' });
        }

        db.prepare(`
            UPDATE products SET
                category_id = ?,
                name = ?,
                description = ?,
                price = ?,
                original_price = ?,
                image_url = ?,
                stock = ?,
                is_featured = ?,
                is_seasonal = ?
            WHERE id = ?
        `).run(
            category_id || null,
            name,
            description || null,
            price,
            original_price || null,
            image_url || null,
            stock || 0,
            is_featured ? 1 : 0,
            is_seasonal ? 1 : 0,
            req.params.id
        );

        const product = db.prepare('SELECT * FROM products WHERE id = ?').get(req.params.id);
        res.json({ message: '產品已更新', product });
    } catch (error) {
        console.error('更新產品錯誤:', error);
        res.status(500).json({ error: '更新產品失敗' });
    }
});

// 刪除產品
router.delete('/products/:id', (req, res) => {
    try {
        // 先確認產品存在
        const existing = db.prepare('SELECT id FROM products WHERE id = ?').get(req.params.id);
        if (!existing) {
            return res.status(404).json({ error: '產品不存在' });
        }

        db.prepare('DELETE FROM products WHERE id = ?').run(req.params.id);

        res.json({ message: '產品已刪除' });
    } catch (error) {
        console.error('刪除產品錯誤:', error);
        res.status(500).json({ error: '刪除產品失敗' });
    }
});

// 取得會員列表
router.get('/members', (req, res) => {
    try {
        const { search, status, limit = 50, offset = 0 } = req.query;

        // 確保 status 欄位存在
        try {
            db.prepare("SELECT status FROM users LIMIT 1").get();
        } catch (e) {
            // 如果欄位不存在，添加它
            db.exec("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'");
            console.log('Added status column to users table');
        }

        let sql = `
            SELECT id, email, name, phone, address, IFNULL(status, 'active') as status, IFNULL(credit, 0) as credit, created_at,
                   (SELECT COUNT(*) FROM orders WHERE user_id = users.id) as order_count,
                   (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE user_id = users.id) as total_spent
            FROM users 
            WHERE is_admin = 0
        `;
        const params = [];

        if (search) {
            sql += ' AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)';
            params.push(`%${search}%`, `%${search}%`, `%${search}%`);
        }

        if (status && status !== 'all') {
            sql += ' AND IFNULL(status, \'active\') = ?';
            params.push(status);
        }

        sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
        params.push(parseInt(limit), parseInt(offset));

        const members = db.prepare(sql).all(...params);

        // 取得總數
        let countSql = 'SELECT COUNT(*) as total FROM users WHERE is_admin = 0';
        const countParams = [];
        if (search) {
            countSql += ' AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)';
            countParams.push(`%${search}%`, `%${search}%`, `%${search}%`);
        }
        if (status && status !== 'all') {
            countSql += ' AND IFNULL(status, \'active\') = ?';
            countParams.push(status);
        }
        const total = db.prepare(countSql).get(...countParams);

        res.json({ members, total: total.total });
    } catch (error) {
        console.error('取得會員錯誤:', error);
        res.status(500).json({ error: '取得會員失敗' });
    }
});

// 更新會員額度
router.put('/members/:id/credit', (req, res) => {
    try {
        const { credit, adjustment } = req.body;
        const memberId = req.params.id;

        // 確保 credit 欄位存在
        try {
            db.prepare("SELECT credit FROM users LIMIT 1").get();
        } catch (e) {
            db.exec("ALTER TABLE users ADD COLUMN credit INTEGER DEFAULT 0");
            console.log('Added credit column to users table');
        }

        const existing = db.prepare('SELECT id, IFNULL(credit, 0) as credit FROM users WHERE id = ? AND is_admin = 0').get(memberId);
        if (!existing) {
            return res.status(404).json({ error: '會員不存在' });
        }

        let newCredit;
        if (typeof adjustment === 'number') {
            // 增減額度
            newCredit = existing.credit + adjustment;
        } else if (typeof credit === 'number') {
            // 直接設定額度
            newCredit = credit;
        } else {
            return res.status(400).json({ error: '請提供有效的額度' });
        }

        if (newCredit < 0) {
            return res.status(400).json({ error: '額度不能為負數' });
        }

        db.prepare('UPDATE users SET credit = ? WHERE id = ?').run(newCredit, memberId);

        res.json({ message: '會員額度已更新', credit: newCredit });
    } catch (error) {
        console.error('更新會員額度錯誤:', error);
        res.status(500).json({ error: '更新會員額度失敗' });
    }
});

// 更新會員狀態
router.put('/members/:id/status', (req, res) => {
    try {
        const { status } = req.body;
        const memberId = req.params.id;

        if (!['active', 'suspended'].includes(status)) {
            return res.status(400).json({ error: '無效的狀態' });
        }

        // 確保 status 欄位存在
        try {
            db.prepare("SELECT status FROM users LIMIT 1").get();
        } catch (e) {
            db.exec("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'");
        }

        const existing = db.prepare('SELECT id FROM users WHERE id = ? AND is_admin = 0').get(memberId);
        if (!existing) {
            return res.status(404).json({ error: '會員不存在' });
        }

        db.prepare('UPDATE users SET status = ? WHERE id = ?').run(status, memberId);

        res.json({ message: '會員狀態已更新', status });
    } catch (error) {
        console.error('更新會員狀態錯誤:', error);
        res.status(500).json({ error: '更新會員狀態失敗' });
    }
});

// 刪除會員
router.delete('/members/:id', (req, res) => {
    try {
        const memberId = req.params.id;

        const existing = db.prepare('SELECT id FROM users WHERE id = ? AND is_admin = 0').get(memberId);
        if (!existing) {
            return res.status(404).json({ error: '會員不存在' });
        }

        // 刪除相關購物車項目
        db.prepare('DELETE FROM cart_items WHERE user_id = ?').run(memberId);

        // 刪除會員
        db.prepare('DELETE FROM users WHERE id = ?').run(memberId);

        res.json({ message: '會員已刪除' });
    } catch (error) {
        console.error('刪除會員錯誤:', error);
        res.status(500).json({ error: '刪除會員失敗' });
    }
});

// 取得分類列表
router.get('/categories', (req, res) => {
    try {
        const categories = db.prepare('SELECT * FROM categories ORDER BY sort_order').all();
        res.json({ categories });
    } catch (error) {
        console.error('取得分類錯誤:', error);
        res.status(500).json({ error: '取得分類失敗' });
    }
});

module.exports = router;
