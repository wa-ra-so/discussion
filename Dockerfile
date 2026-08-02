# --- Stage 1: フロントエンド（Next.js 静的書き出し） ---
FROM node:20-slim AS web-build

WORKDIR /web

COPY web/package.json web/package-lock.json* ./
RUN npm install

COPY web/ ./
# 同一オリジンで配信するため API は相対パス（/api/...）を叩く
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# --- Stage 2: バックエンド（FastAPI）+ フロント静的ファイルの同梱 ---
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schema/ ./schema/
COPY src/ ./src/
COPY --from=web-build /web/out/ ./web_dist/

RUN mkdir -p /app/data/records

ENV DATA_DIR=/app/data
ENV RECORDS_DIR=/app/data/records
ENV DB_PATH=/app/data/db.sqlite
ENV WEB_DIST_DIR=/app/web_dist
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
