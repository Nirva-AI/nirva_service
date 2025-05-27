# utils/redis_client.py
import redis
from fastapi import Depends
from typing import Any


def get_redis() -> Any:
    pool = redis.ConnectionPool(
        host="localhost", port=6379, db=0, decode_responses=True, max_connections=20
    )
    return redis.Redis(connection_pool=pool)


# 使用示例
async def get_session_data(session_id: str, redis: Any = Depends(get_redis)) -> Any:
    return redis.hgetall(f"session:{session_id}")
