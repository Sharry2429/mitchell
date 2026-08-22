# Multi-stage production Dockerfile for Mitchell Autonomous Hive
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

# Install essential system dependencies and virtual X11 display
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    xvfb \
    fluxbox \
    x11vnc \
    espeak \
    ffmpeg \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files and install
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && \
    pip install -e .

# Install Playwright Chromium headless dependencies
RUN playwright install --with-deps chromium

# Copy application source code
COPY mitchell/ ./mitchell/
COPY docs/ ./docs/

# Create non-root user
RUN useradd -m -u 1000 mitchelluser && \
    chown -R mitchelluser:mitchelluser /app
USER mitchelluser

EXPOSE 8000 8500 8765

CMD ["mitchell", "launch", "--api-port", "8000"]
