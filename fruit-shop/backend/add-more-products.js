const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'database.sqlite'));

// 新增2種水果產品
const products = [
    ['金鑽鳳梨', '台南關廟金鑽鳳梨，甜度高，纖維細緻', 259, 329, 80, 5, '/frontend/images/pineapple.png', 1, 1],
    ['茂谷柑橘', '台灣茂谷柑，皮薄汁多，甜中帶酸', 189, 249, 100, 5, '/frontend/images/orange.png', 1, 0]
];

const stmt = db.prepare('INSERT INTO products (name, description, price, original_price, stock, category_id, image_url, is_featured, is_seasonal) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)');

products.forEach(p => {
    try {
        stmt.run(...p);
        console.log('Added:', p[0]);
    } catch (e) {
        console.log('Error:', p[0], e.message);
    }
});

console.log('Done! Total:', db.prepare('SELECT COUNT(*) as c FROM products').get().c);
db.close();
