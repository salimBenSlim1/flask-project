"""Background execution. A small thread pool keeps this free-tier friendly (no worker dyno).

To scale out later, replace `submit` with an RQ/Celery enqueue (Redis is already provisioned);
callers don't change.
"""
from concurrent.futures import ThreadPoolExecutor

from flask import current_app

_executor: ThreadPoolExecutor | None = None


def submit(fn, *args) -> None:
    global _executor
    if current_app.config["INGEST_SYNC"]:
        fn(*args)
        return
    if _executor is None:  # created lazily, i.e. after gunicorn forks
        _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingest")
    _executor.submit(fn, *args)
