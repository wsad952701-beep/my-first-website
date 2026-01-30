// 完整功能測試
const http = require('http');

let authToken = null;

function request(method, path, data = null, token = null) {
    return new Promise((resolve, reject) => {
        const postData = data ? JSON.stringify(data) : '';
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (postData) headers['Content-Length'] = Buffer.byteLength(postData);

        const options = { hostname: 'localhost', port: 3000, path, method, headers };

        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    resolve({ status: res.statusCode, data: JSON.parse(body) });
                } catch (e) {
                    resolve({ status: res.statusCode, data: body });
                }
            });
        });
        req.on('error', reject);
        if (postData) req.write(postData);
        req.end();
    });
}

async function test() {
    console.log('========== 完整功能測試 ==========\n');

    // 1. 註冊
    console.log('1. 測試會員註冊...');
    const reg = await request('POST', '/api/auth/register', {
        email: 'test@example.com', password: 'test123', name: '測試會員'
    });
    console.log(`   結果: ${reg.status === 201 ? '✅ 成功' : '❌ 失敗'} - ${reg.data.message || reg.data.error}`);

    // 2. 登入
    console.log('\n2. 測試會員登入...');
    const login = await request('POST', '/api/auth/login', {
        email: 'test@example.com', password: 'test123'
    });
    console.log(`   結果: ${login.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${login.data.message || login.data.error}`);
    authToken = login.data.token;

    // 3. 管理員登入
    console.log('\n3. 測試管理員登入...');
    const admin = await request('POST', '/api/auth/login', {
        email: 'admin@fruitporter.com', password: 'admin123'
    });
    console.log(`   結果: ${admin.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${admin.data.message || admin.data.error}`);
    console.log(`   管理員權限: ${admin.data.user?.is_admin ? '✅ 是' : '❌ 否'}`);

    // 4. 取得產品
    console.log('\n4. 測試取得產品列表...');
    const products = await request('GET', '/api/products');
    console.log(`   結果: ${products.status === 200 ? '✅ 成功' : '❌ 失敗'} - 共 ${products.data.products?.length || 0} 個產品`);

    // 5. 加入購物車
    console.log('\n5. 測試加入購物車...');
    const addCart = await request('POST', '/api/cart', { product_id: 1, quantity: 1 }, authToken);
    console.log(`   結果: ${addCart.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${addCart.data.message || addCart.data.error}`);

    // 6. 取得購物車
    console.log('\n6. 測試取得購物車...');
    const cart = await request('GET', '/api/cart', null, authToken);
    console.log(`   結果: ${cart.status === 200 ? '✅ 成功' : '❌ 失敗'} - 共 ${cart.data.items?.length || 0} 項，總計 ${cart.data.total || 0}`);

    console.log('\n========== 測試完成 ==========');
}

test().catch(console.error);
