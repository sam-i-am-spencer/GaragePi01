# GaragePi Dockerfile for Raspberry Pi 5
# Uses Python 3.11 slim image for smaller size

FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies for GPIO
# libgpiod2 provides the gpiod library for GPIO control on Pi 5
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgpiod2 \
    libgpiod-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash garagepi

# Change ownership of app files
RUN chown -R garagepi:garagepi /app

# Note: We don't switch to garagepi user because GPIO access requires
# either root or specific group membership. The container runs as root
# but with limited capabilities (see docker-compose.yml)

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
