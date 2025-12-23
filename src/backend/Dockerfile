# Multi-stage build for ViolaDocs Backend with Tesseract OCR
FROM python:3.10-slim as base

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    # Build dependencies for Python packages
    build-essential \
    # Image processing libraries
    libjpeg-dev \
    zlib1g-dev \
    # PDF processing
    poppler-utils \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY alembic.ini .
COPY migrations/ ./migrations/
COPY docker/backend_entrypoint.sh ./docker/
COPY docker/init_root_user.py ./docker/
COPY docker/fix_migration.py ./docker/
RUN chmod +x docker/backend_entrypoint.sh
RUN chmod +x docker/init_root_user.py
RUN chmod +x docker/fix_migration.py

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Use entrypoint script
ENTRYPOINT ["./docker/backend_entrypoint.sh"]

