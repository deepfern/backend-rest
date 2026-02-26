# syntax=docker/dockerfile:1

FROM python:3.8-slim AS runtime

# Keep Python lean & logs unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Workdir
WORKDIR /app

# Install runtime Python deps (all versions are pinned in requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port your app actually listens on (match Helm service.port)
EXPOSE 8080

# Optional: Healthcheck to please some linters/runtimes
# (Hadolint is fine with having or not having HEALTHCHECK, so include only if you want)
# HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
#   CMD python - <<'PY' || exit 1
# import os, socket; s=socket.socket(); s.settimeout(2)
# s.connect(('127.0.0.1', int(os.getenv('FLASK_PORT','5000')))); s.close()
# PY

# Run the application
CMD ["python", "app.py"]
