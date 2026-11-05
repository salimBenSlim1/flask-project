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

# Bake the local embedding model into the image so cold starts don't download it.
# Harmless to skip: if this fails (offline build) the model downloads on first use instead.
ENV FASTEMBED_CACHE_PATH=/srv/models
ARG EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('${EMBEDDING_MODEL}', cache_dir='/srv/models')" \
    || echo "WARNING: embedding model prefetch failed; it will download on first use"
RUN python -m compileall -q app && useradd -m appuser && chown -R appuser /srv
USER appuser

EXPOSE 5000
# Shell form so ${PORT} expands: Render injects PORT, compose/local falls back to 5000.
# --preload loads the app once in the master (db.create_all runs once, not per worker)
CMD ["sh", "-c", "exec gunicorn run:app --preload --worker-class gthread --threads 8 --timeout 120 -b 0.0.0.0:${PORT:-5000} --access-logfile -"]
