# Flowise Component Generator Service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY src/ ./src/

# Copy sample specification file
COPY sample_spec.yaml ./sample_spec.yaml

# Create data directories
RUN mkdir -p /app/data/flowise_components

# Expose port
EXPOSE 8085

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8085/api/flowise/component-generator/health || exit 1

# Run the service
CMD ["python", "src/service.py"]
