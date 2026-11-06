import time
from functools import wraps

from flask import current_app, g

from ..errors import TooManyRequests


def rate_limit(scope: str, config_key: str, window: int = 60):
    """Fixed-window per-user limiter in Redis. Use *under* @login_required.

    Fails open if Redis is unreachable: an outage shouldn't take the feature down.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            limit = current_app.config[config_key]
            now = int(time.time())
            key = f"rl:{scope}:{g.current_user.id}:{now // window}"
            try:
                redis = current_app.extensions["redis"]
                count = redis.incr(key)
                if count == 1:
                    redis.expire(key, window)
            except Exception:
                current_app.logger.warning("Rate limiter unavailable, allowing request")
                return fn(*args, **kwargs)
            if count > limit:
                retry_after = window - (now % window)
                raise TooManyRequests(
                    f"You're asking too fast. Try again in {retry_after}s.",
                    details={"retry_after": retry_after},
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
