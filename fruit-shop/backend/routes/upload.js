const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { authenticateToken } = require('../middleware/auth');

// 設定上傳目錄
const uploadDir = path.join(__dirname, '..', '..', 'frontend', 'images', 'uploads');

// 確保上傳目錄存在
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}

// Multer 設定
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        cb(null, uploadDir);
    },
    filename: function (req, file, cb) {
        // 產生唯一檔名
        const uniqueName = Date.now() + '_' + Math.random().toString(36).substring(7);
        const ext = path.extname(file.originalname);
        cb(null, uniqueName + ext);
    }
});

const upload = multer({
    storage: storage,
    limits: {
        fileSize: 5 * 1024 * 1024 // 5MB 限制
    },
    fileFilter: function (req, file, cb) {
        // 只允許圖片
        if (file.mimetype.startsWith('image/')) {
            cb(null, true);
        } else {
            cb(new Error('只能上傳圖片檔案'));
        }
    }
});

// 上傳圖片
router.post('/', authenticateToken, upload.single('image'), (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: '請選擇圖片檔案' });
        }

        // 回傳圖片網址
        const imageUrl = `/frontend/images/uploads/${req.file.filename}`;
        res.json({
            message: '圖片上傳成功',
            url: imageUrl,
            filename: req.file.filename
        });
    } catch (error) {
        console.error('上傳圖片錯誤:', error);
        res.status(500).json({ error: '上傳圖片失敗' });
    }
});

// 錯誤處理
router.use((error, req, res, next) => {
    if (error instanceof multer.MulterError) {
        if (error.code === 'LIMIT_FILE_SIZE') {
            return res.status(400).json({ error: '檔案太大，最大5MB' });
        }
    }
    res.status(400).json({ error: error.message || '上傳失敗' });
});

module.exports = router;
