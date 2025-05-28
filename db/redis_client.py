import redis
from typing import (
    Dict,
    cast,
    List,
    Optional,
    Union,
    Mapping,
    TYPE_CHECKING,
)
from loguru import logger
from config.configuration import RedisConfig


# Redis键值类型定义
RedisKeyType = Union[str, bytes]
RedisValueType = Union[str, bytes, int, float]

# 为Redis客户端定义明确的类型
if TYPE_CHECKING:
    # 类型检查时使用泛型参数
    RedisClient = redis.Redis[str]
else:
    # 运行时使用的代码 - 避免运行时错误
    RedisClient = redis.Redis  # type: ignore


###################################################################################################
def get_redis() -> "RedisClient":
    """
    获取Redis连接实例。

    返回:
        RedisClient: Redis客户端实例，已配置为返回字符串
    """
    redis_config = RedisConfig()
    pool = redis.ConnectionPool(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        decode_responses=True,
        # max_connections=20
    )
    return cast(RedisClient, redis.Redis(connection_pool=pool))


###################################################################################################
# 获取Redis客户端的单例实例 - 用于直接调用
_redis_instance: Optional[RedisClient] = None


###################################################################################################
def _get_redis_instance() -> RedisClient:
    """
    获取Redis客户端单例实例。

    返回:
        RedisClient: Redis客户端实例
    """
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = get_redis()
    return _redis_instance


###################################################################################################
def redis_hset(name: str, mapping_data: Mapping[str, RedisValueType]) -> None:
    """
    设置Redis哈希表的多个字段。

    参数:
        name: 键名
        mapping_data: 要设置的字段-值映射

    抛出:
        redis.RedisError: 当Redis操作失败时
    """
    try:
        redis_client = _get_redis_instance()
        # 直接使用mapping_data，不需要转换
        redis_client.hset(name=name, mapping=mapping_data)  # type: ignore[arg-type]
    except redis.RedisError as e:
        logger.error(f"Redis error while setting data for {name}: {e}")
        raise e


###################################################################################################
def redis_hgetall(name: str) -> Dict[str, str]:
    """
    获取Redis哈希表中的所有字段和值。

    参数:
        name: 键名

    返回:
        Dict[str, str]: 哈希表中的字段和值

    抛出:
        redis.RedisError: 当Redis操作失败时
    """
    try:
        redis_client = _get_redis_instance()
        if not redis_client.exists(name):
            return {}
        result = redis_client.hgetall(name)
        return {} if result is None else result
    except redis.RedisError as e:
        logger.error(f"Redis error while getting data for {name}: {e}")
        raise e


###################################################################################################
def redis_delete(name: str) -> None:
    """
    删除Redis中的键。

    参数:
        name: 要删除的键名

    抛出:
        redis.RedisError: 当Redis操作失败时
    """
    try:
        redis_client = _get_redis_instance()
        redis_client.delete(name)
    except redis.RedisError as e:
        logger.error(f"Redis error while deleting data for {name}: {e}")
        raise e


###################################################################################################
def redis_lrange(name: str, start: int = 0, end: int = -1) -> List[str]:
    """
    获取Redis列表中指定范围内的元素。

    参数:
        name: 列表键名
        start: 起始索引（默认为0）
        end: 结束索引（默认为-1，表示最后一个元素）

    返回:
        List[str]: 指定范围内的列表元素

    抛出:
        redis.RedisError: 当Redis操作失败时
    """
    try:
        redis_client = _get_redis_instance()
        if not redis_client.exists(name):
            return []
        result = redis_client.lrange(name, start, end)
        return [] if result is None else result
    except redis.RedisError as e:
        logger.error(f"Redis error while getting list range for {name}: {e}")
        raise e


###################################################################################################
def redis_rpush(name: str, *values: str) -> int:
    """
    将一个或多个值添加到Redis列表的右侧。

    参数:
        name: 列表键名
        values: 要添加的值

    返回:
        int: 操作后列表的长度

    抛出:
        redis.RedisError: 当Redis操作失败时
    """
    try:
        redis_client = _get_redis_instance()
        return redis_client.rpush(name, *values)
    except redis.RedisError as e:
        logger.error(f"Redis error while pushing to list {name}: {e}")
        raise e


###################################################################################################


# 要清空 Redis 中的所有数据，您可以使用以下命令：

# 方法一：使用 Redis CLI 命令行工具
# redis-cli flushall
# 这个命令会清空 Redis 中所有数据库的所有数据。

# 方法二：只清空当前数据库
# redis-cli flushdb
# 这个命令只清空当前选择的数据库。

# redis-cli
# HGETALL "session:wei"

# 使用Homebrew安装
# brew install redis

# # 启动Redis服务（开发环境）
# brew services start redis

# # 验证安装
# redis-cli ping
# # 应返回 PONG


# HGETALL "name:Weiwei"
