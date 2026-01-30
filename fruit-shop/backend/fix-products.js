const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'database.sqlite'));

// 修正亂碼產品名稱
const fixes = [
    { id: 13, name: '紐西蘭奇異果', description: '紐西蘭進口奇異果，富含維他命C', price: 280, image_url: '/frontend/images/kiwi.png' },
    { id: 14, name: '日本水蜜桃', description: '日本岡山白桃，香甜多汁', price: 1580, image_url: '/frontend/images/peach.png' },
    { id: 16, name: '進口藍莓', description: '智利進口藍莓，富含花青素', price: 399, image_url: '/frontend/images/grape.png' },
    { id: 17, name: '夏日水果組合', description: '精選3種夏季水果組合', price: 599, image_url: '/frontend/images/watermelon.png' },
    { id: 18, name: '日本麝香葡萄(單串)', description: '日本岡山麝香葡萄單串裝', price: 899, image_url: '/frontend/images/grape.png' }
];

fixes.forEach(f => {
    try {
        db.prepare('UPDATE products SET name = ?, description = ?, image_url = ? WHERE id = ?').run(f.name, f.description, f.image_url, f.id);
        console.log('Fixed:', f.id, f.name);
    } catch (e) {
        console.log('Error:', f.id, e.message);
    }
});

// 新增更多季節水果 (草莓季、櫻桃季、葡萄季)
const newProducts = [
    // 草莓季
    { name: '韓國草莓', description: '韓國雪嶽山草莓，大顆香甜', price: 680, original_price: 880, stock: 50, category_id: 2, image_url: '/frontend/images/strawberry_seasonal_1769721085772.png', is_featured: 1, is_seasonal: 1 },
    { name: '日本栃木草莓', description: '日本栃木縣產，酸甜適中', price: 1280, original_price: 1580, stock: 30, category_id: 4, image_url: '/frontend/images/strawberry_seasonal_1769721085772.png', is_featured: 1, is_seasonal: 1 },
    // 櫻桃季
    { name: '美國櫻桃9.5R', description: '美國華盛頓州大櫻桃', price: 980, original_price: 1280, stock: 40, category_id: 3, image_url: '/frontend/images/cherry_box_1769721098855.png', is_featured: 1, is_seasonal: 1 },
    { name: '紐西蘭櫻桃禮盒', description: '紐西蘭空運櫻桃禮盒裝', price: 1680, original_price: 1980, stock: 25, category_id: 1, image_url: '/frontend/images/cherry_box_1769721098855.png', is_featured: 1, is_seasonal: 1 },
    // 葡萄季  
    { name: '巨峰葡萄', description: '日本進口巨峰葡萄，顆顆飽滿', price: 580, original_price: 780, stock: 60, category_id: 4, image_url: '/frontend/images/grape.png', is_featured: 1, is_seasonal: 1 },
    { name: '貓眼葡萄', description: '日本貓眼葡萄，皮薄多汁', price: 1380, original_price: 1680, stock: 35, category_id: 4, image_url: '/frontend/images/grape_muscat_1769721121816.png', is_featured: 1, is_seasonal: 1 }
];

const stmt = db.prepare('INSERT INTO products (name, description, price, original_price, stock, category_id, image_url, is_featured, is_seasonal) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)');

newProducts.forEach(p => {
    try {
        stmt.run(p.name, p.description, p.price, p.original_price, p.stock, p.category_id, p.image_url, p.is_featured, p.is_seasonal);
        console.log('Added:', p.name);
    } catch (e) {
        if (!e.message.includes('UNIQUE')) {
            console.log('Error adding:', p.name, e.message);
        }
    }
});

console.log('\n=== Final Products ===');
const products = db.prepare('SELECT id, name, price, category_id, is_seasonal FROM products ORDER BY category_id, id').all();
console.log('Total:', products.length);
products.forEach(p => console.log(' -', p.id, p.name, '$' + p.price, 'cat:' + p.category_id, p.is_seasonal ? '🌸季節' : ''));

db.close();
console.log('\n=== Done ===');
