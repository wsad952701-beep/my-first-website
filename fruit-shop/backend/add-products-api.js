// 透過 API 新增水果產品
const products = [
    { category_id: 5, name: '金鑽鳳梨', description: '台南關廟金鑽鳳梨，甜度高，纖維細緻', price: 259, original_price: 329, stock: 80, image_url: '/frontend/images/pineapple.png', is_featured: true, is_seasonal: true },
    { category_id: 5, name: '茂谷柑橘', description: '台灣茂谷柑，皮薄汁多，甜中帶酸', price: 189, original_price: 249, stock: 100, image_url: '/frontend/images/orange.png', is_featured: true, is_seasonal: false },
    { category_id: 5, name: '愛文芒果禮盒', description: '台灣屏東精選愛文芒果，香甜多汁', price: 599, original_price: 799, stock: 50, image_url: '/frontend/images/mango.png', is_featured: true, is_seasonal: true },
    { category_id: 5, name: '花蓮西瓜', description: '花蓮無籽大西瓜，消暑聖品', price: 299, original_price: 399, stock: 30, image_url: '/frontend/images/watermelon.png', is_featured: true, is_seasonal: true }
];

async function addProducts() {
    // 先登入取得 token
    const loginRes = await fetch('http://localhost:3000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'admin@fruitporter.com', password: 'admin123' })
    });
    const loginData = await loginRes.json();
    const token = loginData.token;
    console.log('Login:', loginData.message);

    // 新增每個產品
    for (const product of products) {
        try {
            const res = await fetch('http://localhost:3000/api/admin/products', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(product)
            });
            const data = await res.json();
            console.log('Added:', product.name, data.message || data.error);
        } catch (e) {
            console.log('Error:', product.name, e.message);
        }
    }
    console.log('Done!');
}

addProducts();
