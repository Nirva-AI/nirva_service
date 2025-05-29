from typing import List, Union, final, cast
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from models_v_0_0_1.models import UserSession
import db.redis_user_session
from loguru import logger


###############################################################################################################################################
@final
class UserSessionManager:
    """管理用户会话数据，包括会话存储、检索和更新"""

    ###############################################################################################################################################
    def acquire_user_session(self, user_name: str) -> UserSession:
        """获取用户会话，如果不存在则创建新的会话"""
        assert user_name != "", "user_name cannot be an empty string."

        user_session_from_redis = db.redis_user_session.get_user_session(user_name)
        if (
            user_session_from_redis.user_name == ""
            and len(user_session_from_redis.chat_history) == 0
        ):
            # 不存在就创建一个新的用户会话
            new_session = UserSession(
                user_name=user_name,
                chat_history=[
                    SystemMessage(
                        content="你需要扮演一个海盗与我对话，要用海盗的语气哦！"
                    )
                ],
            )

            logger.info(
                f"Creating new user session for {user_name}: {new_session.model_dump_json()}"
            )

            # 第一次创建用户会话时，存储到 Redis 中
            db.redis_user_session.update_user_session(new_session)
            return new_session

        # 如果用户会话存在，则直接返回
        return user_session_from_redis

    ###############################################################################################################################################
    def store_session_messages(
        self,
        user_session: UserSession,
        messages: List[Union[SystemMessage, HumanMessage, AIMessage]],
    ) -> None:
        """向用户会话添加新消息"""
        db.redis_user_session.add_messages_to_user_session(
            user_session=user_session,
            messages=cast(List[BaseMessage], messages),
        )

    ###############################################################################################################################################
    def delete_user_session(self, user_name: str) -> None:
        """删除用户会话及其聊天历史"""
        assert user_name != "", "user_name cannot be an empty string."
        # 删除用户会话和聊天历史
        db.redis_user_session.delete_user_session(user_name)

    ###############################################################################################################################################
