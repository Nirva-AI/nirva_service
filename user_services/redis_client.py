# utils/redis_client.py
import redis
from typing import Any, Dict, cast
from loguru import logger
from config.configuration import RedisConfig

# 要清空 Redis 中的所有数据，您可以使用以下命令：

# 方法一：使用 Redis CLI 命令行工具
# redis-cli flushall
# 这个命令会清空 Redis 中所有数据库的所有数据。

# 方法二：只清空当前数据库
# redis-cli flushdb
# 这个命令只清空当前选择的数据库。

# redis-cli
# HGETALL "session:wei"


###################################################################################################
def get_redis() -> Any:
    redis_config = RedisConfig()
    pool = redis.ConnectionPool(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        decode_responses=True,
        # max_connections=20
    )
    return redis.Redis(connection_pool=pool)


###################################################################################################
# 获取Redis客户端的单例实例 - 用于直接调用
_redis_instance = None


###################################################################################################
def _get_redis_instance() -> Any:
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = get_redis()
    return _redis_instance


###################################################################################################
def redis_set(name: str, mapping_data: Dict[str, str]) -> None:
    try:
        redis = _get_redis_instance()
        redis.hset(name=name, mapping=mapping_data)
    except redis.RedisError as e:
        logger.error(f"Redis error while setting data for {name}: {e}")
        raise e


###################################################################################################
def redis_get(name: str) -> Dict[str, str]:
    try:
        redis = _get_redis_instance()
        if not redis.exists(name):
            return {}
        return cast(Dict[str, str], redis.hgetall(name)) or {}
    except redis.RedisError as e:
        logger.error(f"Redis error while getting data for {name}: {e}")
        raise e


###################################################################################################
def redis_delete(name: str) -> None:
    try:
        redis = _get_redis_instance()
        redis.delete(name)
    except redis.RedisError as e:
        logger.error(f"Redis error while deleting data for {name}: {e}")
        raise e


###################################################################################################
