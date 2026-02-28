# Flash Loan Trading System - Dockerfile
# Multi-stage build for optimal image size

# ======================== BASE IMAGE ========================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# ======================== DEPENDENCIES ========================
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ======================== BUILD ========================
FROM dependencies as build

# Copy source code
COPY src/ ./src/
COPY config.json .

# Install build dependencies
RUN pip install --no-cache-dir build twine

# Build the package
RUN python -m build

# ======================== PRODUCTION ========================
FROM dependencies as production

# Copy source code
COPY src/ ./src/
COPY config.json .

# Copy built package
COPY --from=build /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Create non-root user for security
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app && \
    mkdir -p /app/data && \
    chown trader:trader /app/data

USER trader

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "src/main.py"]

# ======================== DEVELOPMENT ========================
FROM dependencies as development

# Copy source code
COPY src/ ./src/
COPY config.json .

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio \
    ruff mypy bandit safety pip-audit

# Create non-root user
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app && \
    mkdir -p /app/data && \
    chown trader:trader /app/data

USER trader

# Expose port
EXPOSE 8000

# Development commands
CMD ["python", "src/main.py", "--test"]

# ======================== TESTING ========================
FROM dependencies as testing

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/
COPY config.json .

# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio

# Run tests
CMD ["pytest", "tests/", "-v", "--cov=src", "--cov-report=html"]

# ======================== SECURITY SCAN ========================
FROM dependencies as security-scan

# Copy source code
COPY src/ ./src/

# Install security tools
RUN pip install --no-cache-dir bandit safety pip-audit

# Run security scans
CMD ["bandit", "-r", "src/", "-ll", "&&", "safety", "check", "-r", "requirements.txt"]