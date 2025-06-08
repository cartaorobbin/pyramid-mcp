# Pyramid MCP Secure Example Docker Image
# Multi-stage build for optimized size and security

# =============================================================================
# BUILD STAGE - Install dependencies and build the application
# =============================================================================
FROM python:3.11-slim as builder

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set work directory for build
WORKDIR /build

# Copy pyramid-mcp source code and project files from project root
COPY pyramid_mcp/ ./pyramid_mcp/
COPY pyproject.toml poetry.lock README.md ./

# Configure Poetry: don't create virtual env since we're in container
RUN poetry config virtualenvs.create false

# Build pyramid-mcp wheel
RUN poetry build

# Install pyramid-mcp from wheel
RUN pip install dist/*.whl

# Install additional dependencies needed for secure example
RUN pip install pyramid waitress PyJWT

# Copy examples source code
COPY examples/ ./examples/

# =============================================================================
# RUNTIME STAGE - Create minimal runtime environment
# =============================================================================
FROM python:3.11-slim as runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1000 mcp

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy examples code (pyramid-mcp is already installed in site-packages)
COPY --from=builder /build/examples /app/examples

# Set working directory
WORKDIR /app

# Create non-root user and switch to it for security
USER mcp

# Expose port 8080 for MCP server
EXPOSE 8080

# Health check to ensure container is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/auth/login || exit 1

# Default command - run secure example with context factories
CMD ["python", "examples/secure/secure_app.py"]

# Metadata labels
LABEL maintainer="pyramid-mcp"
LABEL description="Pyramid MCP Secure Example with authentication and context factories"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/your-org/pyramid-mcp" 