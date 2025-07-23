# Build stage
FROM python:3.11-slim-bookworm as django-builder

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libssl-dev \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
COPY requirements.txt .
RUN python3 -m venv /app/virtual && \
    /app/virtual/bin/pip install --upgrade pip && \
    /app/virtual/bin/pip install --no-cache-dir -r requirements.txt && \
    /app/virtual/bin/pip install psycopg2-binary gunicorn python-dotenv

# Runtime stage
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=MUST.settings \
    VIRTUAL_ENV=/app/virtual \
    PATH="/app/virtual/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONOPTIMIZE=1

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 django && \
    useradd -u 1000 -g django -d /app -s /bin/bash django

# Copy virtual environment and project files
COPY --from=django-builder --chown=django:django /app/virtual /app/virtual
COPY --chown=django:django . .

# Copy .env file
COPY --chown=django:django .env .env

# Switch to non-root user
USER django

# Expose port 8000 to match Gunicorn's actual binding
EXPOSE 8000

# Updated CMD to explicitly use port 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "MUST.wsgi:application"]