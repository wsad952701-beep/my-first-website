const express = require('express');
const router = express.Router();
const db = require('../config/database');

// 取得所有分類
router.get('/categories', (req, res) => {
    try {
        const categories = db.prepare('SELECT * FROM categories ORDER BY sort_order').all();
        res.json({ categories });
    } catch (error) {
        console.error('取得分類錯誤:', error);
        res.status(500).json({ error: '取得分類失敗' });
    }
});

// 取得產品列表
router.get('/', (req, res) => {
    try {
        const { category_id, category, featured, seasonal, search, limit = 50, offset = 0 } = req.query;
        const catId = category_id || category; // 支援兩種參數名稱

        let sql = `
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE 1=1
        `;
        const params = [];

        if (catId) {
            sql += ' AND p.category_id = ?';
            params.push(catId);
        }

        if (featured === '1') {
            sql += ' AND p.is_featured = 1';
        }

        if (seasonal === '1') {
            sql += ' AND p.is_seasonal = 1';
        }

        if (search) {
            sql += ' AND (p.name LIKE ? OR p.description LIKE ?)';
            params.push(`%${search}%`, `%${search}%`);
        }

        sql += ' ORDER BY p.is_featured DESC, p.created_at DESC LIMIT ? OFFSET ?';
        params.push(parseInt(limit), parseInt(offset));

        const products = db.prepare(sql).all(...params);

        // 取得總數
        let countSql = sql.replace(/SELECT p\.\*, c\.name as category_name/, 'SELECT COUNT(*) as total')
            .replace(/ORDER BY.*$/, '');
        const countParams = params.slice(0, -2);
        const total = db.prepare(countSql.split('LIMIT')[0]).get(...countParams);

        res.json({
            products,
            total: total ? total.total : products.length
        });
    } catch (error) {
        console.error('取得產品錯誤:', error);
        res.status(500).json({ error: '取得產品失敗' });
    }
});

// 取得精選產品
router.get('/featured', (req, res) => {
    try {
        const products = db.prepare(`
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE p.is_featured = 1
            ORDER BY p.created_at DESC
            LIMIT 8
        `).all();

        res.json({ products });
    } catch (error) {
        console.error('取得精選產品錯誤:', error);
        res.status(500).json({ error: '取得精選產品失敗' });
    }
});

// 取得季節限定產品
router.get('/seasonal', (req, res) => {
    try {
        const products = db.prepare(`
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE p.is_seasonal = 1
            ORDER BY p.created_at DESC
            LIMIT 8
        `).all();

        res.json({ products });
    } catch (error) {
        console.error('取得季節產品錯誤:', error);
        res.status(500).json({ error: '取得季節產品失敗' });
    }
});

// 取得單一產品
router.get('/:id', (req, res) => {
    try {
        const product = db.prepare(`
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE p.id = ?
        `).get(req.params.id);

        if (!product) {
            return res.status(404).json({ error: '產品不存在' });
        }

        res.json({ product });
    } catch (error) {
        console.error('取得產品錯誤:', error);
        res.status(500).json({ error: '取得產品失敗' });
    }
});

module.exports = router;
