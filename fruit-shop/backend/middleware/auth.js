const jwt = require('jsonwebtoken');

const JWT_SECRET = 'fruit-porter-secret-key-2024';

// 驗證 JWT Token
function authenticateToken(req, res, next) {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(401).json({ error: '請先登入' });
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            return res.status(403).json({ error: 'Token 無效或已過期' });
        }
        req.user = user;
        next();
    });
}

// 驗證管理員權限
function requireAdmin(req, res, next) {
    if (!req.user || !req.user.is_admin) {
        return res.status(403).json({ error: '需要管理員權限' });
    }
    next();
}

// 產生 JWT Token
function generateToken(user) {
    return jwt.sign(
        {
            id: user.id,
            email: user.email,
            name: user.name,
            is_admin: user.is_admin
        },
        JWT_SECRET,
        { expiresIn: '7d' }
    );
}

module.exports = {
    authenticateToken,
    requireAdmin,
    generateToken,
    JWT_SECRET
};
