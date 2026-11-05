FROM python:3.12-slim

# Don't write .pyc at runtime (container FS is ephemeral); we precompile at build instead.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Copy requirements first so this layer is cached until dependencies change
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python -m compileall -q app && useradd -m appuser && chown -R appuser /srv
USER appuser

EXPOSE 5000
# Shell form so ${PORT} expands: Render injects PORT, compose/local falls back to 5000.
# --preload loads the app once in the master (db.create_all runs once, not per worker)
CMD ["sh", "-c", "exec gunicorn run:app --preload -b 0.0.0.0:${PORT:-5000} --access-logfile -"]
