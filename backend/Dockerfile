FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# Copy the rest of the backend code
COPY . .

RUN useradd --system --uid 1001 --create-home appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker-entrypoint.sh

# Set Python path so imports like 'crypto_explorer.core...' work
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose API port
EXPOSE 8000

# Start FastAPI server
ENTRYPOINT ["/app/docker-entrypoint.sh"]
