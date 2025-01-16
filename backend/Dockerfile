# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend and core/bess directories into the container
COPY backend/ /app/
COPY core/bess /app/core/bess

# Set the environment variable for Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Run with uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]