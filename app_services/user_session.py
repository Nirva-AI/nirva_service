from models_v_0_0_1.session import UserSession
import db.redis_user_session
from loguru import logger
from datetime import datetime


###############################################################################################################################################
def get_or_create_user_session(username: str) -> UserSession:
    """获取用户会话，如果不存在则创建新的会话"""
    assert username != "", "username cannot be an empty string."

    user_session_from_redis = db.redis_user_session.get_user_session(username)
    if (
        user_session_from_redis.username != ""
        and len(user_session_from_redis.chat_history) > 0
    ):
        # 如果用户会话存在，则直接返回
        logger.info(
            f"User session for {username} already exists: {user_session_from_redis.model_dump_json()}"
        )
        return user_session_from_redis

    # 不存在就创建一个新的用户会话
    new_session = UserSession(
        username=username,
        chat_history=[],
        update_at=datetime.now().isoformat(),
    )

    logger.info(
        f"Creating new user session for {username}: {new_session.model_dump_json()}"
    )

    # 存储到 Redis 中
    db.redis_user_session.set_user_session(new_session)
    return new_session


###############################################################################################################################################
