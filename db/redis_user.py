import db.redis_client
from db.jwt import Token


###############################################################################################################################################
def _user_token_key(username: str) -> str:
    """生成用户会话键名"""
    assert username != "", "username cannot be an empty string."
    return f"token:{username}"


###############################################################################################################################################
def assign_user_token(username: str, token: Token) -> None:
    user_token_key = _user_token_key(username)
    db.redis_client.redis_delete(user_token_key)
    db.redis_client.redis_hset(user_token_key, token.model_dump())
    db.redis_client.redis_expire(user_token_key, seconds=60)  # 设置过期时间为1小时


###############################################################################################################################################
def is_user_token_present(username: str) -> bool:
    user_token_key = _user_token_key(username)
    return db.redis_client.redis_exists(user_token_key)


###############################################################################################################################################
