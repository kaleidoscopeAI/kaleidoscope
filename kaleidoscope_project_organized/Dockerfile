# Multi-stage build for Kaleidoscope AI

# Stage 1: Build dependencies
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies for tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    && npm install -g js-beautify \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m kaleidoscope
RUN mkdir -p /app/kaleidoscope_workdir /app/logs /app/uploads \
    && chown -R kaleidoscope:kaleidoscope /app

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache /wheels/*

# Copy application
COPY . .
RUN pip install -e .

# Use non-root user
USER kaleidoscope

# Configure environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/kaleidoscope/.local/bin:$PATH" \
    CONFIG_PATH="/app/config.json" \
    WORK_DIR="/app/kaleidoscope_workdir"

# Default command
ENTRYPOINT ["python", "-m", "kaleidoscope"]
CMD ["web", "--host", "0.0.0.0"]

# Expose port
EXPOSE 5000
