import redis

from app.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

LOCK_TTL_SECONDS = 30


def acquire_lock(idempotency_key: str) -> bool:
    lock_key = f"checkout_lock:{idempotency_key}"
    return bool(redis_client.set(lock_key, "locked", nx=True, ex=LOCK_TTL_SECONDS))


def release_lock(idempotency_key: str) -> None:
    lock_key = f"checkout_lock:{idempotency_key}"
    redis_client.delete(lock_key)


def check_lock(idempotency_key: str) -> bool:
    lock_key = f"checkout_lock:{idempotency_key}"
    return redis_client.get(lock_key) is not None
