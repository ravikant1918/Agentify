FROM node:18-alpine AS frontend-builder

# Build the React frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ ./
RUN npm run build

# Python backend stage
FROM python:3.13-slim 
ARG PORT
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY="localhost,127.0.0.1"

# Set environment variables for runtime proxy settings
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements and install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Copy built frontend from the frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads

# Set permissions
RUN chmod +x /app/deploy.sh || true

EXPOSE ${PORT:-8001}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8001}/health || exit 1

# Change to backend directory and run the application
WORKDIR /app/backend
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
