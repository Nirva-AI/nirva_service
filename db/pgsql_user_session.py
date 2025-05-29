from db.pgsql_object import UserSessionDB, ChatMessageDB, UserDB
from models_v_0_0_1 import UserSession
from db.pgsql_client import SessionLocal
from typing import Optional
from uuid import UUID
import datetime


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
            # 提取消息类型
            msg_type = message.type

            # 提取消息内容
            content = message.content

            # 提取额外属性
            additional_kwargs = {}
            for key, value in message.dict().items():
                if key not in ["type", "content"]:
                    additional_kwargs[key] = value

            # 创建消息记录
            chat_message = ChatMessageDB(
                session_id=session.id,
                type=msg_type,
                content=content,
                additional_kwargs=additional_kwargs,
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
