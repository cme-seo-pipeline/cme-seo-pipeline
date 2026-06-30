FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline.py .
COPY server.py .

ENV PORT=8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "3600", "--workers", "1", "server:app"]
