FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for building frontend
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json for frontend dependencies
COPY static/package*.json ./static/
RUN cd static && npm install

# Copy application code
COPY . .

# Build frontend CSS
RUN cd static && npm run build-css

# Create uploads and migrations directories
RUN mkdir -p uploads migrations

# Copy database migration files
RUN find . -name "*.sql" -exec cp {} ./migrations/ \; || true

# Expose port
EXPOSE 8000

# Run the application with gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --timeout 120 app:app"]