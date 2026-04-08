import time
import redis
from backend.config import REDIS_URL, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW

r = redis.from_url(REDIS_URL)


def check_rate_limit(api_key: str) -> dict:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    key = f"ratelimit:{api_key}"

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {f"{now}": now})
    pipe.zcard(key)
    pipe.expire(key, RATE_LIMIT_WINDOW)
    results = pipe.execute()

    current_count = results[2]
    remaining = max(0, RATE_LIMIT_MAX - current_count)
    reset_at = int(now + RATE_LIMIT_WINDOW)

    return {
        "allowed": current_count <= RATE_LIMIT_MAX,
        "remaining": remaining,
        "limit": RATE_LIMIT_MAX,
        "reset": reset_at,
    }
