# Use Python 3.13 slim image
FROM docker.io/python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && \
    rm /uv-installer.sh && \
    mv $HOME/.local/bin/uv /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock README.md ./

# Copy application code
COPY idum_proxy /app/idum_proxy

# Install dependencies
RUN uv sync --frozen --no-cache

# Expose port
EXPOSE 8000

# Run the application using uv
CMD ["uv", "run", "python", "-m", "idum_proxy.idum_proxy"]
