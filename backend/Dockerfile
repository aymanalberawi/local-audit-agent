FROM python:3.11-slim

# Install system dependencies for psycopg2 and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Initialize database and then run the API
CMD sh -c 'python init_db.py && uvicorn main:app --host 0.0.0.0 --port 8000'
