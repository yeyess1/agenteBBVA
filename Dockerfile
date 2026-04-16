# Production Dockerfile for Render
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY src /app/src
COPY main.py /app/main.py
COPY start.sh /app/start.sh

# Create data directory
RUN mkdir -p /app/chroma_data && chmod +x /app/start.sh

EXPOSE 10000

# Health check (Render uses port 10000 by default)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

# Use start script to properly handle PORT variable
CMD ["/app/start.sh"]
