const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'backend', 'database.sqlite'));

// Add new fruit products
const products = [
    {
        name: '愛文芒果',
        description: '台灣屏東精選愛文芒果，香甜多汁，果肉細緻，夏季限定美味',
        price: 399,
        original_price: 499,
        stock: 100,
        category_id: 5,
        image_url: '/frontend/images/mango.png',
        is_featured: 1,
        is_seasonal: 1
    },
    {
        name: '花蓮大西瓜',
        description: '花蓮無籽大西瓜，清甜多汁，消暑聖品，每顆約5-6公斤',
        price: 299,
        original_price: 399,
        stock: 50,
        category_id: 5,
        image_url: '/frontend/images/watermelon.png',
        is_featured: 1,
        is_seasonal: 1
    },
    {
        name: '巨峰葡萄',
        description: '日本巨峰葡萄，顆顆飽滿，皮薄肉厚，甜度極高',
        price: 599,
        original_price: 799,
        stock: 80,
        category_id: 4,
        image_url: '/frontend/images/grape.png',
        is_featured: 1,
        is_seasonal: 0
    },
    {
        name: '水蜜桃',
        description: '梨山高山水蜜桃，香氣濃郁，果肉細嫩多汁，甜美誘人',
        price: 499,
        original_price: 699,
        stock: 60,
        category_id: 5,
        image_url: '/frontend/images/peach.png',
        is_featured: 0,
        is_seasonal: 1
    },
    {
        name: '紐西蘭奇異果',
        description: '紐西蘭進口奇異果，富含維他命C，酸甜可口，營養滿分',
        price: 199,
        original_price: 249,
        stock: 120,
        category_id: 3,
        image_url: '/frontend/images/kiwi.png',
        is_featured: 1,
        is_seasonal: 0
    },
    {
        name: '日本蜜柑',
        description: '日本和歌山蜜柑，皮薄易剝，果肉多汁，酸甜適中',
        price: 459,
        original_price: 599,
        stock: 70,
        category_id: 4,
        image_url: '/frontend/images/products/apple-giftbox.jpg',
        is_featured: 0,
        is_seasonal: 1
    }
];

const insertStmt = db.prepare(`
    INSERT INTO products (name, description, price, original_price, stock, category_id, image_url, is_featured, is_seasonal)
    VALUES (@name, @description, @price, @original_price, @stock, @category_id, @image_url, @is_featured, @is_seasonal)
`);

let count = 0;
for (const product of products) {
    try {
        insertStmt.run(product);
        count++;
        console.log(`✓ Added: ${product.name}`);
    } catch (e) {
        console.log(`Skip (may exist): ${product.name}`);
    }
}

console.log(`\nDone! Added ${count} new products.`);
db.close();
