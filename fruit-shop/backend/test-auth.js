// 測試認證 API
const http = require('http');

function testAPI(method, path, data) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify(data);
        const options = {
            hostname: 'localhost',
            port: 3000,
            path: path,
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                console.log(`[${res.statusCode}] ${path}`);
                console.log(body);
                resolve({ status: res.statusCode, body: JSON.parse(body) });
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

async function runTests() {
    console.log('=== 測試會員註冊 ===');
    try {
        const registerResult = await testAPI('POST', '/api/auth/register', {
            email: 'newuser@test.com',
            password: 'password123',
            name: '新用戶'
        });
        console.log('註冊結果:', registerResult.body);
    } catch (e) {
        console.error('註冊錯誤:', e.message);
    }

    console.log('\n=== 測試會員登入 ===');
    try {
        const loginResult = await testAPI('POST', '/api/auth/login', {
            email: 'newuser@test.com',
            password: 'password123'
        });
        console.log('登入結果:', loginResult.body);
    } catch (e) {
        console.error('登入錯誤:', e.message);
    }

    console.log('\n=== 測試管理員登入 ===');
    try {
        const adminResult = await testAPI('POST', '/api/auth/login', {
            email: 'admin@fruitporter.com',
            password: 'admin123'
        });
        console.log('管理員登入結果:', adminResult.body);
    } catch (e) {
        console.error('管理員登入錯誤:', e.message);
    }
}

runTests();
