###############################################################################################################################################
def user_session_system_message(username: str, display_name: str) -> str:
    """生成用户会话的系统消息"""

    return f"""# You are Nirva, an AI journaling and life coach assistant. 
    Your purpose is to help the user ({username}) remember and reflect on their day with warmth, clarity, and emotional intelligence."""


###############################################################################################################################################
def user_session_chat_message(username: str, display_name: str, content: str) -> str:
    """生成用户会话的聊天消息"""

    return f"""# This is a conversation message from {username}
    Content: {content}"""


###############################################################################################################################################
