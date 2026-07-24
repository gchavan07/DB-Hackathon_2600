# ── Build stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# OpenShift runs containers as a random non-root UID – this makes it work
RUN mkdir -p /app && chown -R 1001:0 /app && chmod -R g=u /app
WORKDIR /app

# Install dependencies first (layer cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application source
COPY . .

# Ensure output/input dirs exist and are writable by any UID (OpenShift requirement)
RUN mkdir -p output input_docs .agent && chmod -R g=u /app

# Switch to non-root user (OpenShift compatibility)
USER 1001

# ── Runtime ───────────────────────────────────────────────────────────────
# PORT is injected by OpenShift / Kubernetes. Falls back to 8080.
ENV PORT=8080 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
