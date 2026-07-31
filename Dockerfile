FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
