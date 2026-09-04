import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, status
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("interviewos.rate_limit")

# In-memory fallback tracking {key: [timestamps]}
_memory_store: Dict[str, List[float]] = defaultdict(list)
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                socket_timeout=1.0,
                decode_responses=True,
            )
        except Exception:
            _redis_client = None
    return _redis_client


class RateLimiter:
    """Async rate limiter supporting Redis with resilient in-memory fallback."""

    enabled: bool = True

    def __init__(self, times: int = 10, seconds: int = 60, prefix: str = "rl"):
        self.times = times
        self.seconds = seconds
        self.prefix = prefix

    @classmethod
    def reset(cls):
        _memory_store.clear()

    async def __call__(self, request: Request):
        if not self.enabled or not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return

        # Extract client IP
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"{self.prefix}:{client_ip}:{path}"

        now = time.time()
        redis = await get_redis_client()

        # 1. Try Redis first
        if redis:
            try:
                # Sliding window with Redis sorted set
                pipeline = redis.pipeline()
                pipeline.zremrangebyscore(key, 0, now - self.seconds)
                pipeline.zadd(key, {str(now): now})
                pipeline.zcard(key)
                pipeline.expire(key, self.seconds)
                _, _, count, _ = await pipeline.execute()

                if count > self.times:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded: Max {self.times} requests per {self.seconds} seconds. Please slow down.",
                        headers={"Retry-After": str(self.seconds)},
                    )
                return
            except HTTPException:
                raise
            except Exception as e:
                logger.debug("Redis rate limit check failed, using in-memory fallback: %s", e)

        # 2. In-memory fallback
        timestamps = _memory_store[key]
        # Purge expired timestamps
        cutoff = now - self.seconds
        _memory_store[key] = [t for t in timestamps if t > cutoff]

        if len(_memory_store[key]) >= self.times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: Max {self.times} requests per {self.seconds} seconds. Please slow down.",
                headers={"Retry-After": str(self.seconds)},
            )

        _memory_store[key].append(now)
