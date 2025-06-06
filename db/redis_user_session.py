from models_v_0_0_1 import UserSession
from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import db.redis_client
import json
from loguru import logger
from datetime import datetime


###############################################################################################################################################
def _user_session_key(username: str) -> str:
    """生成用户会话键名"""
    assert username != "", "username cannot be an empty string."
    return f"session:{username}"


###############################################################################################################################################
def _user_history_key(username: str) -> str:
    """生成用户聊天历史键名"""
    assert username != "", "username cannot be an empty string."
    return f"session:{username}:history"


###############################################################################################################################################
def _serialize_message(message: BaseMessage) -> str:
    """将消息对象序列化为JSON字符串"""
    return json.dumps(
        {
            "type": message.type,
            "message": message.model_dump_json(),
        }
    )


###############################################################################################################################################
def _deserialize_message(message_json: str) -> Optional[BaseMessage]:
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
def get_user_session(username: str) -> UserSession:
    user_session_key = _user_session_key(username)
    user_session_data = db.redis_client.redis_hgetall(user_session_key)
    if user_session_data == {} or user_session_data is None:
        # 如果用户会话不存在，返回一个空的 UserSession 对象
        return UserSession(
            username="",
            chat_history=[],
            update_at=datetime.now().isoformat(),
        )

    # 获取对话历史
    history_key = _user_history_key(username)
    redis_history_data = db.redis_client.redis_lrange(history_key, 0, -1)
    chat_history: List[BaseMessage] = []
    for message_json in redis_history_data:
        message = _deserialize_message(message_json)
        if message:
            logger.debug(f"Deserialized message: {message}")
            chat_history.append(message)

    return UserSession(
        username=username,
        chat_history=chat_history,
        update_at=user_session_data.get("update_at", datetime.now().isoformat()),
    )


###############################################################################################################################################


def set_user_session(user_session: UserSession) -> None:

    assert user_session.username != "", "username cannot be an empty string."

    """更新用户会话，包括基本信息和聊天历史"""
    user_session_key = _user_session_key(user_session.username)

    # 更新用户基本信息
    db.redis_client.redis_hset(
        user_session_key,
        {
            "username": user_session.username,
            "update_at": user_session.update_at,
        },
    )

    # 更新聊天历史
    history_key = _user_history_key(user_session.username)

    # 首先删除旧的聊天历史
    db.redis_client.redis_delete(history_key)

    # 然后添加新的聊天历史
    if user_session.chat_history:
        for message in user_session.chat_history:
            message_json = _serialize_message(message)
            db.redis_client.redis_rpush(history_key, message_json)


###############################################################################################################################################


def delete_user_session(username: str) -> None:
    """删除用户会话及其聊天历史"""
    assert username != "", "username cannot be an empty string."
    # 删除用户会话和聊天历史
    db.redis_client.redis_delete(_user_session_key(username))
    db.redis_client.redis_delete(_user_history_key(username))


###############################################################################################################################################
def append_messages_to_session(
    user_session: UserSession,
    new_messages: List[BaseMessage],
) -> None:

    user_session_key = _user_session_key(user_session.username)
    # 更新用户基本信息
    db.redis_client.redis_hset(
        user_session_key,
        {
            "username": user_session.username,
            "update_at": user_session.update_at,
        },
    )

    # 更新Redis中的聊天历史
    history_key = _user_history_key(user_session.username)
    for message in new_messages:
        message_json = _serialize_message(message)
        db.redis_client.redis_rpush(history_key, message_json)


###############################################################################################################################################
