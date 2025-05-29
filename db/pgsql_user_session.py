from db.pgsql_object import UserSessionDB, ChatMessageDB, UserDB
from models_v_0_0_1 import UserSession
from db.pgsql_client import SessionLocal
from typing import Optional, List
from uuid import UUID
import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage


############################################################################################################
def save_user_session(
    user_session: UserSession,
    session_id: Optional[UUID] = None,
    session_name: Optional[str] = None,
) -> UUID:
    """
    将UserSession对象存储到PostgreSQL数据库

    参数:
        user_session: 要保存的UserSession对象
        session_id: 可选的会话ID，如果提供则更新现有会话，否则创建新会话
        session_name: 可选的会话名称

    返回:
        会话ID (UUID)
    """
    db = SessionLocal()
    try:
        # 查找用户，如果不存在则抛出异常
        user = db.query(UserDB).filter_by(username=user_session.user_name).first()
        if not user:
            raise ValueError(f"用户 '{user_session.user_name}' 不存在")

        # 创建或更新会话
        if session_id:
            # 更新现有会话
            session = db.query(UserSessionDB).filter_by(id=session_id).first()
            if not session:
                raise ValueError(f"会话ID '{session_id}' 不存在")

            # 更新会话时间
            session.updated_at = datetime.datetime.utcnow()

            # 如果提供了新的会话名称，则更新
            if session_name:
                session.session_name = session_name

            # 删除现有消息
            db.query(ChatMessageDB).filter_by(session_id=session_id).delete()
        else:
            # 创建新的会话
            session = UserSessionDB(user_id=user.id, session_name=session_name)
            db.add(session)
            db.flush()  # 获取新生成的ID

        # 存储聊天消息
        for index, message in enumerate(user_session.chat_history):
            # 序列化整个消息对象
            message_dict = message.model_dump()

            # 创建消息记录
            chat_message = ChatMessageDB(
                session_id=session.id,
                type=message.type,  # 仍保留类型字段便于查询
                message_data=message_dict,
                order_index=index,
            )
            db.add(chat_message)

        # 提交事务
        db.commit()
        return session.id

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()


############################################################################################################
def get_user_session(user_name: str, session_id: UUID) -> UserSession:
    """
    从数据库读取用户会话数据

    参数:
        user_name: 用户名
        session_id: 会话ID

    返回:
        UserSession对象
    """
    db = SessionLocal()
    try:
        # 检查用户是否存在
        user = db.query(UserDB).filter_by(username=user_name).first()
        if not user:
            raise ValueError(f"用户 '{user_name}' 不存在")

        # 获取会话
        session = (
            db.query(UserSessionDB).filter_by(id=session_id, user_id=user.id).first()
        )
        if not session:
            raise ValueError(f"会话ID '{session_id}' 不存在或不属于用户 '{user_name}'")

        # 获取会话消息
        messages_db = (
            db.query(ChatMessageDB)
            .filter_by(session_id=session_id)
            .order_by(ChatMessageDB.order_index)
            .all()
        )

        # 重建消息历史
        chat_history: List[BaseMessage] = []
        for msg_db in messages_db:
            # 根据消息类型选择正确的消息类
            msg_data = msg_db.message_data
            msg_type = msg_data.get("type")
            msg_obj: Optional[BaseMessage] = None

            if msg_type == "human":
                msg_obj = HumanMessage.model_validate(msg_data)
            elif msg_type == "ai":
                msg_obj = AIMessage.model_validate(msg_data)
            elif msg_type == "system":
                msg_obj = SystemMessage.model_validate(msg_data)
            else:
                # 处理其他可能的消息类型
                continue

            assert msg_obj is not None, f"Unknown message type: {msg_type}"
            chat_history.append(msg_obj)

        # 构建并返回UserSession
        return UserSession(user_name=user_name, chat_history=chat_history)

    finally:
        db.close()


############################################################################################################
