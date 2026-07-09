FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY worker /app

EXPOSE 9100

CMD ["python", "-m", "app.main"]
