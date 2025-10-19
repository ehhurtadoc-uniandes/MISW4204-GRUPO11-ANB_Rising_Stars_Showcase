FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libfontconfig1 \
    libglib2.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgstreamer1.0-0 \
    libpq-dev \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app

# Copy Alembic configuration and migrations
COPY alembic.ini /app/
COPY ./alembic /app/alembic

# Copy initialization scripts
COPY ./scripts /app/scripts

# Create necessary directories
RUN mkdir -p /app/uploads /app/processed_videos /app/assets /app/logs

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash anb
RUN chown -R anb:anb /app
USER anb

# Expose port
EXPOSE 8000

# Default command - usar script de inicio
CMD ["/app/scripts/start.sh"]