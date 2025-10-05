FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt
# Use uv to install dependencies into the system interpreter
RUN uv pip install --system -r /app/requirements.txt

# Copy app code
COPY . /app

# Default environment
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Expose FastAPI default port (optional if only CLI is used)
EXPOSE 8000

# Default command just shows help; override via docker-compose
CMD ["python", "-m", "src.cli", "--help"]

