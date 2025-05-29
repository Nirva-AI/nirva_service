"""
psql -U fastapi_user -d my_fastapi_db

查看用户会话表
SELECT id, user_id, session_name, created_at, updated_at 
FROM user_sessions;

查看消息内容
SELECT cm.id, cm.session_id, cm.type, cm.content, cm.order_index, cm.created_at
FROM chat_messages cm
JOIN user_sessions us ON cm.session_id = us.id
WHERE us.session_name = '测试会话'
ORDER BY cm.order_index;

查看完整关联数据
SELECT 
    u.username,
    us.id AS session_id,
    us.session_name,
    cm.type AS message_type,
    cm.content,
    cm.order_index,
    cm.created_at
FROM users u
JOIN user_sessions us ON u.id = us.user_id
JOIN chat_messages cm ON us.id = cm.session_id
WHERE u.username = 'test_user1'
ORDER BY us.created_at, cm.order_index;
"""

# 对于较长的内容，可以使用 \x 命令切换到扩展显示模式：
# \x on
# SELECT * FROM chat_messages LIMIT 3;
# \x off


############################################################################################################
def main() -> None:
    # 如何使用该函数
    from models_v_0_0_1 import UserSession
    from langchain_core.messages import HumanMessage, AIMessage
    from db.pgsql_opt import save_user_session, save_user

    save_user(
        user_name="test_user1",
        hashed_password="13dadasdasdqeqeqeqda",
    )

    # 创建一个用户会话
    user_session = UserSession(
        user_name="test_user1",
        chat_history=[
            HumanMessage(content="你好，我是用户"),
            AIMessage(content="你好，我是AI助手"),
        ],
    )

    # 保存会话
    session_id = save_user_session(user_session, session_name="测试会话")
    print(f"保存的会话ID: {session_id}")

    # 更新现有会话
    updated_user_session = UserSession(
        user_name="test_user1",
        chat_history=[
            HumanMessage(content="你好，我是用户"),
            AIMessage(content="你好，我是AI助手"),
            HumanMessage(content="我有一个问题"),
        ],
    )
    save_user_session(updated_user_session, session_id=session_id)


############################################################################################################
if __name__ == "__main__":
    main()
