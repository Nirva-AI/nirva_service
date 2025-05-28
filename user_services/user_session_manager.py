from typing import List, Union
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import user_services.redis_client
from pydantic import BaseModel
import json


###############################################################################################################################################
class UserSession(BaseModel):
    user_name: str
    chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []


###############################################################################################################################################
class UserSessionManager:

    ###############################################################################################################################################
    def _user_session_key(self, user_name: str) -> str:
        assert user_name != "", "user_name cannot be an empty string."
        return f"session:{user_name}"

    ###############################################################################################################################################
    def _user_history_key(self, user_name: str) -> str:
        assert user_name != "", "user_name cannot be an empty string."
        return f"session:{user_name}:history"

    ###############################################################################################################################################
    def acquire_user_session(self, user_name: str) -> UserSession:

        user_session_key = self._user_session_key(user_name)
        user_session_data = user_services.redis_client.redis_hgetall(user_session_key)

        if user_session_data == {} or user_session_data is None:
            # 不存在就创建一个新的用户会话。
            new_session = UserSession(
                user_name=user_name,
                chat_history=[
                    SystemMessage(
                        content="你需要扮演一个海盗与我对话，要用海盗的语气哦！"
                    )
                ],
            )

            # 第一次创建用户会话时，存储到 Redis 中。
            self._update_user_session(new_session)
            return new_session

        # 如果存在，就从 Redis 中获取用户会话数据。
        history_key = self._user_history_key(user_name)
        redis_history_data = user_services.redis_client.redis_lrange(history_key, 0, -1)

        # 将 Redis 中的聊天历史数据转换为 UserSession 对象。
        chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []
        for message_json in redis_history_data:
            message_data = json.loads(message_json)
            message_type = message_data["type"]
            message_content = message_data["message"]

            if message_type == "system":
                chat_history.append(SystemMessage.model_validate_json(message_content))
            elif message_type == "human":
                chat_history.append(HumanMessage.model_validate_json(message_content))
            elif message_type == "ai":
                chat_history.append(AIMessage.model_validate_json(message_content))

        return UserSession(
            user_name=user_name,
            chat_history=chat_history,
        )

    ###############################################################################################################################################
    def add_messages_to_user_session(
        self,
        user_session: UserSession,
        messages: List[Union[SystemMessage, HumanMessage, AIMessage]],
    ) -> None:

        user_session.chat_history.extend(messages)

        # 更新用户会话
        history_key = self._user_history_key(user_session.user_name)
        for message in messages:
            message_json = json.dumps(
                {
                    "type": message.type,
                    "message": message.model_dump_json(),
                }
            )
            user_services.redis_client.redis_rpush(history_key, message_json)

    ###############################################################################################################################################
    def _update_user_session(self, user_session: UserSession) -> None:

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
                message_json = json.dumps(
                    {
                        "type": message.type,
                        "message": message.model_dump_json(),
                    }
                )
                user_services.redis_client.redis_rpush(history_key, message_json)

    ###############################################################################################################################################
    def delete_user_session(self, user_name: str) -> None:
        user_session_key = self._user_session_key(user_name)
        history_key = self._user_history_key(user_name)

        # 删除用户会话和聊天历史
        user_services.redis_client.redis_delete(user_session_key)
        user_services.redis_client.redis_delete(history_key)

    ###############################################################################################################################################
