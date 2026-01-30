// 完整功能測試 - 包含訂單建立
const http = require('http');

let userToken = null;
let adminToken = null;

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
    console.log('╔══════════════════════════════════════════════════════════╗');
    console.log('║           果實搬運工 - 完整功能測試                      ║');
    console.log('╚══════════════════════════════════════════════════════════╝\n');

    // 1. 會員註冊
    console.log('【1】會員註冊');
    const reg = await request('POST', '/api/auth/register', {
        email: 'buyer@test.com', password: 'test123', name: '測試買家', phone: '0912345678'
    });
    console.log(`    結果: ${reg.status === 201 ? '✅ 成功' : '❌ 失敗'} - ${reg.data.message || reg.data.error}`);
    userToken = reg.data.token;

    // 2. 管理員登入
    console.log('\n【2】管理員登入');
    const admin = await request('POST', '/api/auth/login', {
        email: 'admin@fruitporter.com', password: 'admin123'
    });
    console.log(`    結果: ${admin.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${admin.data.message || admin.data.error}`);
    console.log(`    是管理員: ${admin.data.user?.is_admin ? '✅ 是' : '❌ 否'}`);
    adminToken = admin.data.token;

    // 3. 取得產品列表
    console.log('\n【3】產品列表');
    const products = await request('GET', '/api/products');
    console.log(`    結果: ${products.status === 200 ? '✅ 成功' : '❌ 失敗'} - 共 ${products.data.products?.length || 0} 個產品`);
    const hasImages = products.data.products?.filter(p => p.image_url).length || 0;
    console.log(`    有圖片的產品: ${hasImages} 個`);

    // 4. 加入購物車
    console.log('\n【4】加入購物車');
    const add1 = await request('POST', '/api/cart', { product_id: 1, quantity: 1 }, userToken);
    console.log(`    產品1: ${add1.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${add1.data.message || add1.data.error}`);
    const add2 = await request('POST', '/api/cart', { product_id: 3, quantity: 2 }, userToken);
    console.log(`    產品3: ${add2.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${add2.data.message || add2.data.error}`);

    // 5. 取得購物車
    console.log('\n【5】購物車內容');
    const cart = await request('GET', '/api/cart', null, userToken);
    console.log(`    結果: ${cart.status === 200 ? '✅ 成功' : '❌ 失敗'} - 共 ${cart.data.items?.length || 0} 項`);
    console.log(`    總金額: NT$ ${cart.data.total || 0}`);

    // 6. 建立訂單 (關鍵測試!)
    console.log('\n【6】建立訂單');
    const order = await request('POST', '/api/orders', {
        shipping_name: '測試收件人',
        shipping_phone: '0912345678',
        shipping_address: '台北市中正區測試路100號'
    }, userToken);
    console.log(`    結果: ${order.status === 201 ? '✅ 成功' : '❌ 失敗'} - ${order.data.message || order.data.error}`);
    if (order.data.order) {
        console.log(`    訂單編號: ${order.data.order.order_number}`);
        console.log(`    訂單金額: NT$ ${order.data.order.total_amount}`);
    }

    // 7. 後台 - 取得所有訂單
    console.log('\n【7】後台訂單管理');
    const adminOrders = await request('GET', '/api/admin/orders', null, adminToken);
    console.log(`    結果: ${adminOrders.status === 200 ? '✅ 成功' : '❌ 失敗'} - 共 ${adminOrders.data.orders?.length || 0} 筆訂單`);

    // 8. 後台 - 取得訂單詳情
    if (order.data.order) {
        console.log('\n【8】後台訂單詳情');
        const orderDetail = await request('GET', `/api/admin/orders/${order.data.order.id}`, null, adminToken);
        console.log(`    結果: ${orderDetail.status === 200 ? '✅ 成功' : '❌ 失敗'}`);
        console.log(`    訂單項目: ${orderDetail.data.items?.length || 0} 項`);
    }

    // 9. 後台 - 更新訂單狀態
    if (order.data.order) {
        console.log('\n【9】更新訂單狀態');
        const updateStatus = await request('PUT', `/api/admin/orders/${order.data.order.id}/status`,
            { status: 'processing' }, adminToken);
        console.log(`    結果: ${updateStatus.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${updateStatus.data.message || updateStatus.data.error}`);
    }

    // 10. 後台 - 產品管理
    console.log('\n【10】後台產品管理');
    const adminProducts = await request('GET', '/api/admin/products', null, adminToken);
    console.log(`    取得產品: ${adminProducts.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${adminProducts.data.products?.length || 0} 個`);

    // 更新產品價格
    const updateProduct = await request('PUT', '/api/admin/products/1', {
        category_id: 1,
        name: '新年豪華禮盒',
        description: '精選日本蘋果、韓國水梨、進口柑橘組合',
        price: 2999,
        original_price: 3500,
        stock: 50,
        image_url: '/frontend/images/gift_box_premium_1769721412356.png',
        is_featured: true,
        is_seasonal: false
    }, adminToken);
    console.log(`    更新價格: ${updateProduct.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${updateProduct.data.message || updateProduct.data.error}`);

    // 11. 後台儀表板
    console.log('\n【11】後台儀表板');
    const dashboard = await request('GET', '/api/admin/dashboard', null, adminToken);
    console.log(`    結果: ${dashboard.status === 200 ? '✅ 成功' : '❌ 失敗'}`);
    if (dashboard.data.today) {
        console.log(`    今日訂單: ${dashboard.data.today.orders} 筆`);
        console.log(`    今日營收: NT$ ${dashboard.data.today.revenue}`);
    }

    // 12. 會員列表
    console.log('\n【12】會員管理');
    const members = await request('GET', '/api/admin/members', null, adminToken);
    console.log(`    結果: ${members.status === 200 ? '✅ 成功' : '❌ 失敗'} - ${members.data.members?.length || 0} 位會員`);

    console.log('\n╔══════════════════════════════════════════════════════════╗');
    console.log('║                    測試完成                              ║');
    console.log('╚══════════════════════════════════════════════════════════╝');
}

test().catch(console.error);
