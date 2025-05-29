from typing import List, Union, final, cast
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from models_v_0_0_1.models import UserSession
import db.redis_user_session
import db.pgsql_user_session
from loguru import logger
from uuid import uuid4


###############################################################################################################################################
@final
class UserSessionManager:
    """管理用户会话数据，包括会话存储、检索和更新"""

    ###############################################################################################################################################
    def acquire_user_session(self, user_name: str) -> UserSession:
        """获取用户会话，如果不存在则创建新的会话"""
        assert user_name != "", "user_name cannot be an empty string."

        user_session_from_redis = db.redis_user_session.get_user_session(user_name)
        if user_session_from_redis.session_id is not None:
            # 如果用户会话存在，则直接返回
            logger.info(
                f"User session for {user_name} already exists: {user_session_from_redis.model_dump_json()}"
            )
            return user_session_from_redis

        # 如果用户会话不存在，从数据库中获取
        user_sessions_from_db = db.pgsql_user_session.get_user_sessions(user_name)
        if len(user_sessions_from_db) == 0:
            # 不存在就创建一个新的用户会话
            new_session = UserSession(
                user_name=user_name,
                chat_history=[
                    SystemMessage(
                        content="你需要扮演一个海盗与我对话，要用海盗的语气哦！"
                    )
                ],
                session_id=uuid4(),  # 生成一个新的UUID作为会话ID
            )

            logger.info(
                f"Creating new user session for {user_name}: {new_session.model_dump_json()}"
            )

            # 第一次创建用户会话时，存储到 Redis 和 PostgreSQL 中
            db.redis_user_session.set_user_session(new_session)
            db.pgsql_user_session.set_user_session(
                new_session, session_id=new_session.session_id
            )
            return new_session

        # 存在于数据库中但不在 Redis 中
        # 取第一个会话作为用户会话
        user_session_from_db = user_sessions_from_db[0]
        logger.info(
            f"User session for {user_name} found in database: {user_session_from_db.model_dump_json()}"
        )
        # 将会话存储到 Redis 中
        db.redis_user_session.set_user_session(user_session_from_db)
        return user_session_from_db

    ###############################################################################################################################################
    def update_user_session_with_new_messages(
        self,
        user_session: UserSession,
        messages: List[Union[SystemMessage, HumanMessage, AIMessage]],
    ) -> None:
        """向用户会话添加新消息"""
        db.redis_user_session.update_user_session(
            user_session=user_session,
            new_messages=cast(List[BaseMessage], messages),
        )

        assert (
            user_session.session_id is not None
        ), "user_session.session_id cannot be None."
        db.pgsql_user_session.update_user_session(
            user_session=user_session,
            new_messages=cast(List[BaseMessage], messages),
            session_id=user_session.session_id,
        )

    ###############################################################################################################################################
    def stop_user_session(self, user_name: str) -> None:
        """删除用户会话及其聊天历史"""
        assert user_name != "", "user_name cannot be an empty string."
        # 从 Redis 中删除用户会话
        db.redis_user_session.delete_user_session(user_name)

    ###############################################################################################################################################
