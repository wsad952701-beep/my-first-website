const initSqlJs = require('sql.js');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcryptjs');

const dbPath = path.join(__dirname, '..', 'database.sqlite');

let db = null;

// 初始化資料庫
async function initDatabase() {
    const SQL = await initSqlJs();

    // 如果資料庫檔案存在，載入它
    if (fs.existsSync(dbPath)) {
        const buffer = fs.readFileSync(dbPath);
        db = new SQL.Database(buffer);
    } else {
        db = new SQL.Database();
    }

    // 建立資料表
    db.run(`
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            is_admin INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            credit INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // 系統設定表
    db.run(`
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `);

    db.run(`
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📦',
            sort_order INTEGER DEFAULT 0
        )
    `);

    db.run(`
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            original_price REAL,
            stock INTEGER DEFAULT 0,
            image_url TEXT,
            is_featured INTEGER DEFAULT 0,
            is_seasonal INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    `);

    db.run(`
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    `);

    db.run(`
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_number TEXT UNIQUE NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            shipping_name TEXT,
            shipping_phone TEXT,
            shipping_address TEXT,
            notes TEXT,
            cancel_reason TEXT,
            admin_note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    `);

    // 嘗試添加新欄位（如果表已存在但欄位不存在）
    try { db.run('ALTER TABLE orders ADD COLUMN cancel_reason TEXT'); } catch (e) { }
    try { db.run('ALTER TABLE orders ADD COLUMN admin_note TEXT'); } catch (e) { }

    db.run(`
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER,
            name TEXT NOT NULL,
            unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    `);

    // 我的最愛表
    db.run(`
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(user_id, product_id)
        )
    `);

    // 初始化預設資料
    await initDefaultData();

    // 儲存資料庫
    saveDatabase();

    console.log('資料庫初始化完成');
    return db;
}

// 儲存資料庫到檔案
function saveDatabase() {
    if (db) {
        const data = db.export();
        const buffer = Buffer.from(data);
        fs.writeFileSync(dbPath, buffer);
    }
}

// 初始化預設資料
async function initDefaultData() {
    // 檢查是否已有分類
    const catResult = db.exec('SELECT COUNT(*) as count FROM categories');
    const categoryCount = catResult.length > 0 ? catResult[0].values[0][0] : 0;

    if (categoryCount === 0) {
        console.log('建立預設分類...');
        const categories = [
            ['春節禮盒', '🎁', 1],
            ['季節限定', '✨', 2],
            ['進口水果', '🌍', 3],
            ['日本嚴選', '🇯🇵', 4],
            ['台灣在地', '🇹🇼', 5],
            ['優惠專區', '💰', 6]
        ];

        categories.forEach(([name, icon, order]) => {
            db.run('INSERT INTO categories (name, icon, sort_order) VALUES (?, ?, ?)', [name, icon, order]);
        });
    }

    // 檢查是否已有商品
    const prodResult = db.exec('SELECT COUNT(*) as count FROM products');
    const productCount = prodResult.length > 0 ? prodResult[0].values[0][0] : 0;

    if (productCount === 0) {
        console.log('建立預設商品...');
        const products = [
            [1, '新年豪華禮盒', '精選日本蘋果、韓國水梨、進口柑橘組合', 2880, 3200, 50, '/frontend/images/gift_box_premium_1769721412356.png', 1, 0],
            [1, '經典水果禮盒', '台灣精緻水果組合，送禮自用兩相宜', 1680, 1880, 100, '/frontend/images/hero_banner_fruits_1769721071654.png', 1, 0],
            [2, '日本草莓 - 博多甘王', '熊本縣產，甜度超高的頂級草莓', 980, null, 30, '/frontend/images/strawberry_seasonal_1769721085772.png', 1, 1],
            [2, '台灣茂谷柑', '季節限定，外皮薄、果肉多汁', 450, null, 80, '/frontend/images/apple_aomori_1769721134815.png', 0, 1],
            [3, '智利櫻桃 Jumbo', '大顆飽滿，外銷等級櫻桃', 1280, 1500, 20, '/frontend/images/cherry_box_1769721098855.png', 1, 0],
            [3, '美國無籽綠葡萄', '清甜脆口，無籽品種', 380, null, 60, '/frontend/images/grape_muscat_1769721121816.png', 0, 0],
            [4, '日本青森蘋果', '知名青森縣產，紅潤飽滿', 720, null, 40, '/frontend/images/apple_aomori_1769721134815.png', 1, 0],
            [4, '日本晴王麝香葡萄', '頂級麝香葡萄，皮薄肉甜', 1980, 2200, 15, '/frontend/images/grape_muscat_1769721121816.png', 1, 1],
            [5, '大樹鳳梨', '高雄大樹產，鳳梨酸甜適中', 280, null, 100, '/frontend/images/hero_banner_fruits_1769721071654.png', 0, 1],
            [5, '愛文芒果', '屏東枋山產愛文，香甜可口', 580, null, 50, '/frontend/images/strawberry_seasonal_1769721085772.png', 1, 1],
            [6, '綜合季節水果 5斤裝', '當季水果隨機組合', 599, 780, 200, '/frontend/images/hero_banner_fruits_1769721071654.png', 0, 0],
            [6, '香蕉一串', '台灣本土香蕉，營養滿分', 69, 89, 300, '/frontend/images/apple_aomori_1769721134815.png', 0, 0]
        ];

        products.forEach(([cat_id, name, desc, price, orig_price, stock, img, featured, seasonal]) => {
            db.run(
                'INSERT INTO products (category_id, name, description, price, original_price, stock, image_url, is_featured, is_seasonal) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                [cat_id, name, desc, price, orig_price, stock, img, featured, seasonal]
            );
        });
    }

    // 檢查是否已有管理員
    const adminResult = db.exec("SELECT COUNT(*) as count FROM users WHERE is_admin = 1");
    const adminCount = adminResult.length > 0 ? adminResult[0].values[0][0] : 0;

    if (adminCount === 0) {
        console.log('建立預設管理員...');
        const hashedPassword = bcrypt.hashSync('admin123', 10);
        db.run(
            'INSERT INTO users (email, password_hash, name, is_admin) VALUES (?, ?, ?, ?)',
            ['admin@fruitporter.com', hashedPassword, '系統管理員', 1]
        );
    }

    saveDatabase();
}

// 查詢函數封裝
function prepare(sql) {
    return {
        run: (...params) => {
            db.run(sql, params);
            saveDatabase();
            return {
                changes: db.getRowsModified(),
                lastInsertRowid: getLastInsertRowId()
            };
        },
        get: (...params) => {
            const stmt = db.prepare(sql);
            stmt.bind(params);
            if (stmt.step()) {
                const row = stmt.getAsObject();
                stmt.free();
                return row;
            }
            stmt.free();
            return undefined;
        },
        all: (...params) => {
            const results = [];
            const stmt = db.prepare(sql);
            stmt.bind(params);
            while (stmt.step()) {
                results.push(stmt.getAsObject());
            }
            stmt.free();
            return results;
        }
    };
}

function getLastInsertRowId() {
    const result = db.exec('SELECT last_insert_rowid() as id');
    return result.length > 0 ? result[0].values[0][0] : 0;
}

// 建立兼容 better-sqlite3 的介面
const dbInterface = {
    prepare: (sql) => prepare(sql),
    exec: (sql) => db.run(sql),
    transaction: (fn) => {
        return (...args) => {
            db.run('BEGIN TRANSACTION');
            try {
                const result = fn(...args);
                db.run('COMMIT');
                saveDatabase();
                return result;
            } catch (error) {
                db.run('ROLLBACK');
                throw error;
            }
        };
    }
};

// 匯出
module.exports = dbInterface;
module.exports.initDatabase = initDatabase;
