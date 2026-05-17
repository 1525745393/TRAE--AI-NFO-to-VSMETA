# NFO to VSMETA Converter Dockerfile
# Multi-stage build for optimized image size

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt .

# Install dependencies to wheels
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ==============================================================================
# Stage 2: Production
# ==============================================================================
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Create app directory
WORKDIR $APP_HOME

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels

# Install wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser $APP_HOME

# Switch to non-root user
USER appuser

# ==============================================================================
# Stage 3: Development
# ==============================================================================
FROM production as development

# Install development dependencies
RUN pip install --no-cache-dir \
    black \
    mypy \
    pytest \
    pytest-cov \
    flake8 \
    ipython

# Set development environment
ENV FLASK_ENV=development

# Default command
CMD ["python", "-i"]

# ==============================================================================
# Final stage labels
# ==============================================================================
FROM production as final

# Labels
LABEL maintainer="NFO to VSMETA Team <support@example.com>" \
      description="NFO to VSMETA Converter - Convert Kodi NFO files to Synology VSMETA format" \
      version="2.0.1" \
      python.version="3.11"

# Expose ports
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000')" || exit 1

# Default command
ENTRYPOINT ["python", "nfo_to_vsmeta_converter_complete.py"]

# If no arguments provided, show help
CMD ["--help"]
