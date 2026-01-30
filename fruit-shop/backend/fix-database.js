const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'database.sqlite'));

// 添加 credit 欄位到 users 表
try {
    db.exec("ALTER TABLE users ADD COLUMN credit INTEGER DEFAULT 0");
    console.log('✓ Added credit column to users table');
} catch (e) {
    if (e.message.includes('duplicate column')) {
        console.log('✓ Credit column already exists');
    } else {
        console.log('Error:', e.message);
    }
}

// 確認用戶數量
const users = db.prepare('SELECT id, name, email FROM users WHERE is_admin = 0').all();
console.log('\nMembers:', users.length);
users.forEach(u => console.log('  -', u.id, u.name, u.email));

// 確認產品數量
const products = db.prepare('SELECT id, name, price FROM products ORDER BY id DESC').all();
console.log('\nProducts:', products.length);
products.slice(0, 10).forEach(p => console.log('  -', p.id, p.name, '$' + p.price));

db.close();
console.log('\n=== Done ===');
