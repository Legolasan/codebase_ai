# Multi-stage build for smaller image size
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Export dependencies to requirements.txt
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --extras all

# Production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install -e .

# Create directory for ChromaDB data
RUN mkdir -p /data/chroma_db

# Set environment defaults
ENV CHROMA_PERSIST_DIR=/data/chroma_db
ENV PERMISSION_MODE=ask

# Create non-root user for security
RUN useradd -m -u 1000 assistant
RUN chown -R assistant:assistant /app /data
USER assistant

# Default command
ENTRYPOINT ["assistant"]
CMD ["--help"]
