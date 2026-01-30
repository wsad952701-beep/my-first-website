const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const db = require('../config/database');
const { authenticateToken, generateToken } = require('../middleware/auth');

// 會員註冊
router.post('/register', (req, res) => {
    try {
        const { email, password, name, phone } = req.body;

        if (!email || !password || !name) {
            return res.status(400).json({ error: '請填寫必要欄位' });
        }

        // 檢查 email 是否已存在
        const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(email);
        if (existing) {
            return res.status(400).json({ error: '此 Email 已被註冊' });
        }

        // 加密密碼
        const hashedPassword = bcrypt.hashSync(password, 10);

        // 新增用戶
        db.prepare(
            'INSERT INTO users (email, password_hash, name, phone) VALUES (?, ?, ?, ?)'
        ).run(email, hashedPassword, name, phone || null);

        // 用 email 查詢剛建立的用戶
        const user = db.prepare('SELECT id, email, name, phone, is_admin FROM users WHERE email = ?').get(email);
        const token = generateToken(user);

        res.status(201).json({
            message: '註冊成功',
            user: {
                id: user.id,
                email: user.email,
                name: user.name
            },
            token
        });
    } catch (error) {
        console.error('註冊錯誤:', error);
        res.status(500).json({ error: '註冊失敗，請稍後再試' });
    }
});

// 會員登入
router.post('/login', (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({ error: '請輸入 Email 和密碼' });
        }

        // 查找用戶
        const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
        if (!user) {
            return res.status(401).json({ error: 'Email 或密碼錯誤' });
        }

        // 驗證密碼
        if (!bcrypt.compareSync(password, user.password_hash)) {
            return res.status(401).json({ error: 'Email 或密碼錯誤' });
        }

        // 檢查帳號是否被停用
        if (user.status === 'suspended') {
            return res.status(403).json({ error: '您的帳號已被停用，請聯繫客服' });
        }

        const token = generateToken(user);

        res.json({
            message: '登入成功',
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
                is_admin: user.is_admin
            },
            token
        });
    } catch (error) {
        console.error('登入錯誤:', error);
        res.status(500).json({ error: '登入失敗，請稍後再試' });
    }
});

// 取得會員資料
router.get('/profile', authenticateToken, (req, res) => {
    try {
        const user = db.prepare(
            'SELECT id, email, name, phone, address, is_admin, IFNULL(credit, 0) as credit, created_at FROM users WHERE id = ?'
        ).get(req.user.id);

        if (!user) {
            return res.status(404).json({ error: '用戶不存在' });
        }

        res.json({ user });
    } catch (error) {
        console.error('取得資料錯誤:', error);
        res.status(500).json({ error: '取得資料失敗' });
    }
});

// 更新會員資料
router.put('/profile', authenticateToken, (req, res) => {
    try {
        const { name, phone, address } = req.body;

        db.prepare(
            'UPDATE users SET name = ?, phone = ?, address = ? WHERE id = ?'
        ).run(name, phone, address, req.user.id);

        const user = db.prepare(
            'SELECT id, email, name, phone, address FROM users WHERE id = ?'
        ).get(req.user.id);

        res.json({ message: '更新成功', user });
    } catch (error) {
        console.error('更新資料錯誤:', error);
        res.status(500).json({ error: '更新資料失敗' });
    }
});

module.exports = router;
