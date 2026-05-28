# Chess Elegante - Production Docker Image
FROM --platform=linux/amd64 python:3.12-slim

# Build arguments for deployment metadata
ARG COMMIT_SHA=unknown

# Set as environment variable
ENV COMMIT_SHA=${COMMIT_SHA}

# Install system dependencies including Stockfish
RUN apt-get update && apt-get install -y \
    stockfish \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 5000

# Run with gunicorn for production
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
