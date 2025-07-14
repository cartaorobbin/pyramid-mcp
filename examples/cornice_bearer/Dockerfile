FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry files
COPY pyproject.toml ./
COPY ../../pyproject.toml ../../poetry.lock /pyramid-mcp/

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    cd /pyramid-mcp && poetry install --no-dev && \
    cd /app && poetry install --no-dev

# Copy application code
COPY cornice_bearer_app.py ./

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/api/public/info || exit 1

# Run the application
CMD ["python", "cornice_bearer_app.py"] 