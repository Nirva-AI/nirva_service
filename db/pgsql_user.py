from db.pgsql_object import UserDB
from db.pgsql_client import SessionLocal


############################################################################################################
def save_user(username: str, hashed_password: str, display_name: str) -> UserDB:
    """
    保存用户到PostgreSQL数据库

    参数:
        username: 用户名
        hashed_password: 哈希后的密码

    返回:
        UserDB 对象
    """
    db = SessionLocal()
    try:
        user = UserDB(
            username=username,
            hashed_password=hashed_password,
            display_name=display_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


############################################################################################################
def has_user(username: str) -> bool:
    """
    检查用户是否存在于PostgreSQL数据库中

    参数:
        username: 用户名

    返回:
        bool: 如果用户存在返回True，否则返回False
    """
    db = SessionLocal()
    try:
        user_exists = db.query(UserDB).filter_by(username=username).first() is not None
        return user_exists
    finally:
        db.close()


############################################################################################################
def get_user(username: str) -> UserDB:
    """
    从PostgreSQL数据库获取用户

    参数:
        username: 用户名

    返回:
        UserDB 对象
    """
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter_by(username=username).first()
        if not user:
            raise ValueError(f"用户 '{username}' 不存在")
        return user
    finally:
        db.close()


############################################################################################################
