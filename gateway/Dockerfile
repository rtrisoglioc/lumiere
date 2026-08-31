FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Cloud Run provides $PORT (default 8080)
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
