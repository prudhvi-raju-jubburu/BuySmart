FROM python:3.12-slim

# Install system dependencies for Chrome / Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set up environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5001

WORKDIR /app

# Copy requirements and install dependencies

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy application files
COPY backend/ .

# Expose port and run the Flask application
EXPOSE 5001
# CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "2", "--timeout", "120"]
CMD ["sh", "-c", "gunicorn run:app --bind 0.0.0.0:${PORT:-5001} --workers 1 --threads 2 --timeout 120"]