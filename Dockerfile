# syntax=docker/dockerfile:1
FROM python:3.10-slim

# 1) Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    CACHE_DIR=/app/.cache

# 2) Cài đặt hệ thống
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3) Copy và cài Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy toàn bộ code
COPY . .

# 5) Expose port Gradio
EXPOSE 7860

# 6) Command mặc định
CMD ["python", "Source/app.py"]
