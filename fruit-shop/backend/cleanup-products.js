const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'database.sqlite'));

console.log('=== Current Products ===');
const products = db.prepare('SELECT id, name, price, category_id, image_url FROM products ORDER BY id DESC').all();
console.log('Total:', products.length);

// Find duplicates by name
const nameCount = {};
products.forEach(p => {
    nameCount[p.name] = (nameCount[p.name] || 0) + 1;
});

console.log('\nDuplicates:');
Object.keys(nameCount).filter(n => nameCount[n] > 1).forEach(n => {
    console.log(' -', n, 'x', nameCount[n]);
});

// Remove duplicates (keep newest)
const seen = new Set();
const toDelete = [];
products.forEach(p => {
    if (seen.has(p.name)) {
        toDelete.push(p.id);
    } else {
        seen.add(p.name);
    }
});

if (toDelete.length > 0) {
    console.log('\nDeleting duplicates:', toDelete.length);
    toDelete.forEach(id => {
        db.prepare('DELETE FROM products WHERE id = ?').run(id);
        console.log(' - Deleted ID:', id);
    });
}

// Show categories
console.log('\n=== Categories ===');
const cats = db.prepare('SELECT id, name, icon FROM categories').all();
cats.forEach(c => console.log(' -', c.id, c.icon, c.name));

console.log('\n=== Products After Cleanup ===');
const finalProducts = db.prepare('SELECT id, name, price, category_id FROM products ORDER BY category_id, id').all();
console.log('Total:', finalProducts.length);
finalProducts.forEach(p => console.log(' -', p.id, p.name, '$' + p.price, 'cat:' + p.category_id));

db.close();
console.log('\n=== Done ===');
