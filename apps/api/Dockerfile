FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/ ./apps/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
