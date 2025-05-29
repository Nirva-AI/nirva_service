"""
psql -U fastapi_user -d my_fastapi_db

查看用户会话表
SELECT id, user_id, session_name, created_at, updated_at 
FROM user_sessions;

-- 查看测试用户
SELECT id, username FROM users WHERE username = 'test_user1';

-- 查看所有用户
SELECT * FROM users;

-- 查看所有会话
SELECT id, user_id, session_name, created_at, updated_at 
FROM user_sessions;

-- 查看特定用户的会话
SELECT s.id, s.session_name, s.created_at, s.updated_at 
FROM user_sessions s
JOIN users u ON s.user_id = u.id
WHERE u.username = 'test_user1';


-- 启用扩展显示模式(更易阅读JSON数据)

-- 查看所有消息
SELECT id, session_id, type, order_index, message_data
FROM chat_messages
ORDER BY session_id, order_index;

-- 只查看消息内容
SELECT session_id, type, order_index, message_data->>'content' AS content
FROM chat_messages
ORDER BY session_id, order_index;

-- 查看用户、会话和消息的关联数据
SELECT 
    u.username, 
    s.session_name, 
    m.type, 
    m.order_index, 
    m.message_data->>'content' AS content
FROM users u
JOIN user_sessions s ON u.id = s.user_id
JOIN chat_messages m ON s.id = m.session_id
ORDER BY s.id, m.order_index;

-- 替换下面的UUID为你在测试输出中看到的session_id
SELECT type, order_index, message_data->>'content' AS content
FROM chat_messages
WHERE session_id = '替换为实际的会话UUID'
ORDER BY order_index;
"""


############################################################################################################
def main() -> None:
    # 如何使用该函数
    from models_v_0_0_1 import UserSession
    from langchain_core.messages import HumanMessage, AIMessage
    from db.pgsql_user_session import set_user_session
    from db.pgsql_user import save_user, has_user
    from loguru import logger
    from config.test_user_account import simu_test_user_account

    if not has_user(simu_test_user_account.username):
        save_user(
            user_name=simu_test_user_account.username,
            hashed_password=simu_test_user_account.password,
        )

    try:

        # 创建一个用户会话
        user_session = UserSession(
            user_name=simu_test_user_account.username,
            chat_history=[
                HumanMessage(
                    content=f"你好，我是用户[{simu_test_user_account.username}]"
                ),
                AIMessage(content="你好，我是AI助手"),
            ],
        )

        # 保存会话
        session_id = set_user_session(user_session, session_name="测试会话")
        print(f"保存的会话ID: {session_id}")

        # 更新现有会话
        updated_user_session = UserSession(
            user_name=simu_test_user_account.username,
            chat_history=[
                HumanMessage(
                    content=f"你好，我是用户[{simu_test_user_account.username}]"
                ),
                AIMessage(content="你好，我是AI助手"),
                HumanMessage(content="我有一个问题"),
            ],
        )
        set_user_session(updated_user_session, session_id=session_id)
        logger.debug(f"更新的会话ID: {session_id}")

    except Exception as e:
        logger.error(f"发生错误: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
