// 更新產品圖片和新增5款水果
const initSqlJs = require('sql.js');
const path = require('path');
const fs = require('fs');

const dbPath = path.join(__dirname, 'database.sqlite');

async function updateProducts() {
    const SQL = await initSqlJs();
    const buffer = fs.readFileSync(dbPath);
    const db = new SQL.Database(buffer);

    // 更新現有產品圖片
    const updates = [
        [1, '/frontend/images/gift_box_newyear_1769844937612.png'],
        [2, '/frontend/images/gift_box_classic_1769844951179.png'],
        [3, '/frontend/images/strawberry_hakata_1769844965546.png'],
        [4, '/frontend/images/tangerine_maogu_1769844979524.png'],
        [5, '/frontend/images/cherry_jumbo_1769845006620.png'],
        [6, '/frontend/images/grape_green_1769845019750.png'],
        [7, '/frontend/images/apple_aomori_1769845034559.png'],
        [8, '/frontend/images/grape_muscat_1769845047647.png'],
        [9, '/frontend/images/pineapple_dashu_1769845077278.png'],
        [10, '/frontend/images/mango_aiwen_1769845089844.png'],
        [11, '/frontend/images/fruit_mix_box_1769845101821.png'],
        [12, '/frontend/images/banana_taiwan_1769845115102.png']
    ];

    updates.forEach(([id, img]) => {
        db.run('UPDATE products SET image_url = ? WHERE id = ?', [img, id]);
    });

    // 新增5款水果產品
    const newProducts = [
        [3, '紅肉火龍果', '越南進口，鮮豔紅肉，富含花青素', 280, 350, 60, '/frontend/images/dragonfruit_red_1769845145180.png', 0, 1],
        [4, '日本水蜜桃', '山梨縣產白桃，果肉細緻多汁', 1580, 1880, 25, '/frontend/images/peach_japan_1769845159395.png', 1, 1],
        [3, '紐西蘭黃金奇異果', 'Zespri黃金奇異果，酸甜可口', 320, null, 80, '/frontend/images/kiwi_gold_1769845173011.png', 0, 0],
        [5, '台灣木瓜', '屏東產紅肉木瓜，香甜營養', 180, null, 100, '/frontend/images/papaya_taiwan_1769845185740.png', 0, 1],
        [3, '泰國榴槤 貓山王', '馬來西亞貓山王品種，濃郁綿密', 2880, 3500, 10, '/frontend/images/durian_premium_1769845199680.png', 1, 0]
    ];

    newProducts.forEach(([cat_id, name, desc, price, orig_price, stock, img, featured, seasonal]) => {
        db.run(
            'INSERT INTO products (category_id, name, description, price, original_price, stock, image_url, is_featured, is_seasonal) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [cat_id, name, desc, price, orig_price, stock, img, featured, seasonal]
        );
    });

    // 儲存資料庫
    const data = db.export();
    const bufferOut = Buffer.from(data);
    fs.writeFileSync(dbPath, bufferOut);

    console.log('產品更新完成！');
    console.log('已更新 12 個產品圖片');
    console.log('已新增 5 款水果產品');
}

updateProducts();
