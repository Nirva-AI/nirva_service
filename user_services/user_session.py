from langchain_core.messages import SystemMessage
from models_v_0_0_1.models import UserSession
import db.redis_user_session
import db.pgsql_user_session
from loguru import logger
import prompt.builtin as builtin_prompt


###############################################################################################################################################
def get_or_create_user_session(username: str) -> UserSession:
    """获取用户会话，如果不存在则创建新的会话"""
    assert username != "", "username cannot be an empty string."

    user_session_from_redis = db.redis_user_session.get_user_session(username)
    if user_session_from_redis.session_id is not None:
        # 如果用户会话存在，则直接返回
        logger.info(
            f"User session for {username} already exists: {user_session_from_redis.model_dump_json()}"
        )
        return user_session_from_redis

    # 如果用户会话不存在，从数据库中获取
    user_sessions_from_db = db.pgsql_user_session.get_user_sessions(username)
    if len(user_sessions_from_db) == 0:
        # 不存在就创建一个新的用户会话
        new_session = UserSession(
            username=username,
            chat_history=[
                SystemMessage(
                    content=builtin_prompt.user_session_system_message(username)
                ),
            ],
        )

        logger.info(
            f"Creating new user session for {username}: {new_session.model_dump_json()}"
        )

        # 将新会话存储到 PostgreSQL 数据库中, 并第一次生成 session_id
        new_session.session_id = db.pgsql_user_session.set_user_session(new_session)

        # 存储到 Redis 中
        db.redis_user_session.set_user_session(new_session)

        return new_session

    # 存在于数据库中但不在 Redis 中 取第一个会话作为用户会话
    user_session_from_db = user_sessions_from_db[0]
    logger.info(
        f"User session for {username} found in database: {user_session_from_db.model_dump_json()}"
    )
    # 将会话存储到 Redis 中
    db.redis_user_session.set_user_session(user_session_from_db)
    return user_session_from_db


###############################################################################################################################################
