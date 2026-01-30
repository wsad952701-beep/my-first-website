# PFZ System Docker Image
# 潛在漁場預測系統

FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PFZ_ENV=production

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 建立快取目錄
RUN mkdir -p /app/cache

# 設定非 root 用戶
RUN useradd -m -u 1000 pfz && chown -R pfz:pfz /app
USER pfz

# 預設命令
CMD ["python", "main.py", "--help"]

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pfz_system; print('OK')" || exit 1
