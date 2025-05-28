from typing import List, Union, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import user_services.redis_client
from pydantic import BaseModel
import json
from loguru import logger


###############################################################################################################################################
class UserSession(BaseModel):
    user_name: str
    chat_history: List[BaseMessage] = []


###############################################################################################################################################
class UserSessionManager:
    """管理用户会话数据，包括会话存储、检索和更新"""

    ###############################################################################################################################################
    def _user_session_key(self, user_name: str) -> str:
        """生成用户会话键名"""
        assert user_name != "", "user_name cannot be an empty string."
        return f"session:{user_name}"

    ###############################################################################################################################################
    def _user_history_key(self, user_name: str) -> str:
        """生成用户聊天历史键名"""
        assert user_name != "", "user_name cannot be an empty string."
        return f"session:{user_name}:history"

    ###############################################################################################################################################
    def _serialize_message(self, message: BaseMessage) -> str:
        """将消息对象序列化为JSON字符串"""
        return json.dumps(
            {
                "type": message.type,
                "message": message.model_dump_json(),
            }
        )

    ###############################################################################################################################################
    def _deserialize_message(self, message_json: str) -> Optional[BaseMessage]:
        """将JSON字符串反序列化为消息对象"""
        try:
            message_data = json.loads(message_json)
            message_type = message_data.get("type")
            message_content = message_data.get("message", "{}")

            if message_type == "system":
                return SystemMessage.model_validate_json(message_content)
            elif message_type == "human":
                return HumanMessage.model_validate_json(message_content)
            elif message_type == "ai":
                return AIMessage.model_validate_json(message_content)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error deserializing message: {e}")
            return None

    ###############################################################################################################################################
    def acquire_user_session(self, user_name: str) -> UserSession:
        """获取用户会话，如果不存在则创建新的会话"""
        assert user_name != "", "user_name cannot be an empty string."
        user_session_key = self._user_session_key(user_name)
        user_session_data = user_services.redis_client.redis_hgetall(user_session_key)

        if user_session_data == {} or user_session_data is None:
            # 不存在就创建一个新的用户会话
            new_session = UserSession(
                user_name=user_name,
                chat_history=[
                    SystemMessage(
                        content="你需要扮演一个海盗与我对话，要用海盗的语气哦！"
                    )
                ],
            )
            # 第一次创建用户会话时，存储到 Redis 中
            self._update_user_session(new_session)
            return new_session

        # 如果存在，就从 Redis 中获取聊天历史
        history_key = self._user_history_key(user_name)
        redis_history_data = user_services.redis_client.redis_lrange(history_key, 0, -1)

        # 将 Redis 中的聊天历史数据转换为消息对象
        chat_history: List[BaseMessage] = []
        for message_json in redis_history_data:
            message = self._deserialize_message(message_json)
            if message:
                chat_history.append(message)

        return UserSession(user_name=user_name, chat_history=chat_history)

    ###############################################################################################################################################
    def add_messages_to_user_session(
        self,
        user_session: UserSession,
        messages: List[Union[SystemMessage, HumanMessage, AIMessage]],
    ) -> None:
        """向用户会话添加新消息"""
        # 更新内存中的会话对象
        user_session.chat_history.extend(messages)
        # 更新Redis中的聊天历史
        history_key = self._user_history_key(user_session.user_name)
        for message in messages:
            message_json = self._serialize_message(message)
            user_services.redis_client.redis_rpush(history_key, message_json)

    ###############################################################################################################################################
    def _update_user_session(self, user_session: UserSession) -> None:
        """更新用户会话，包括基本信息和聊天历史"""
        user_session_key = self._user_session_key(user_session.user_name)

        # 更新用户基本信息
        user_services.redis_client.redis_hset(
            user_session_key,
            {
                "user_name": user_session.user_name,
            },
        )

        # 更新聊天历史
        history_key = self._user_history_key(user_session.user_name)

        # 首先删除旧的聊天历史
        user_services.redis_client.redis_delete(history_key)

        # 然后添加新的聊天历史
        if user_session.chat_history:
            for message in user_session.chat_history:
                message_json = self._serialize_message(message)
                user_services.redis_client.redis_rpush(history_key, message_json)

    ###############################################################################################################################################
    def delete_user_session(self, user_name: str) -> None:
        """删除用户会话及其聊天历史"""
        assert user_name != "", "user_name cannot be an empty string."
        # 删除用户会话和聊天历史
        user_services.redis_client.redis_delete(self._user_session_key(user_name))
        user_services.redis_client.redis_delete(self._user_history_key(user_name))

    ###############################################################################################################################################
