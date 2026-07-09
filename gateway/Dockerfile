FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

COPY gateway/requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY gateway /app

EXPOSE 5023 5024

CMD ["python", "-m", "app.main"]
