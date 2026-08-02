FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# openai-whisper の setup.py が pkg_resources に依存しており、
# 新しい setuptools（pkg_resources を含まない）だとビルドに失敗するため、
# ビルド用の隔離環境にも適用される制約ファイルで setuptools を固定する。
RUN echo "setuptools<81" > /tmp/constraints.txt
ENV PIP_CONSTRAINT=/tmp/constraints.txt
RUN pip install --no-cache-dir -r requirements.txt

# Whisper モデルをビルド時に取り込んでおく（実行時ダウンロードだと初回リクエストが
# 遅延・タイムアウトする上、コンテナ再起動のたびに再ダウンロードが発生してしまうため）。
RUN python -c "import whisper; whisper.load_model('base')"

COPY schema/ ./schema/
COPY src/ ./src/

RUN mkdir -p /app/data/audio /app/data/records

ENV DATA_DIR=/app/data
ENV AUDIO_DIR=/app/data/audio
ENV RECORDS_DIR=/app/data/records
ENV DB_PATH=/app/data/db.sqlite
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
