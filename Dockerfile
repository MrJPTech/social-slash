FROM python:3.12-slim

WORKDIR /app

# Install system packages for reliable HTTPS and DNS resolution.
# ca-certificates: ensures TLS handshakes succeed for Late API, Supabase, etc.
# curl: used by HEALTHCHECK to verify networking from inside the container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-mcp.txt .
RUN pip install --no-cache-dir -r requirements-mcp.txt

# Copy application code
COPY lib/ lib/
COPY data/*.json data/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Verify Late API is reachable (catches DNS/networking issues early)
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf https://getlate.dev/api > /dev/null || exit 1

# Auto-detects transport: stdio (no PORT) or streamable-http (PORT set)
CMD ["python", "-m", "lib.mcp"]
