#!/bin/bash

# FastAPI サーバーを起動
# 使用法: ./run_api.sh
# API は http://localhost:8000 でリッスン
# ドキュメント: http://localhost:8000/docs

source venv/bin/activate 2>/dev/null || source venv/Scripts/activate
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
