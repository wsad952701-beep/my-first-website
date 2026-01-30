const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'database.sqlite'));

// 新增6種水果產品
const products = [
    ['愛文芒果', '台灣屏東精選愛文芒果，香甜多汁', 399, 499, 100, 5, '/frontend/images/mango.png', 1, 1],
    ['花蓮大西瓜', '花蓮無籽大西瓜，消暑聖品', 299, 399, 50, 5, '/frontend/images/watermelon.png', 1, 1],
    ['巨峰葡萄', '日本巨峰葡萄，顆顆飽滿', 599, 799, 80, 4, '/frontend/images/grape.png', 1, 0],
    ['水蜜桃', '梨山高山水蜜桃，香氣濃郁', 499, 699, 60, 5, '/frontend/images/peach.png', 1, 1],
    ['紐西蘭奇異果', '紐西蘭進口奇異果，富含維他命C', 199, 249, 120, 3, '/frontend/images/kiwi.png', 1, 0],
    ['日本蜜柑', '日本和歌山蜜柑，皮薄易剝', 459, 599, 70, 4, '/frontend/images/grape.png', 1, 1]
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
