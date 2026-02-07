FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements-mcp.txt .
RUN pip install --no-cache-dir -r requirements-mcp.txt

# Copy application code
COPY lib/ lib/
COPY data/platform_templates.json data/platform_templates.json
COPY data/queue_config.json data/queue_config.json

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Auto-detects transport: stdio (no PORT) or SSE (PORT set)
CMD ["python", "-m", "lib.mcp"]
