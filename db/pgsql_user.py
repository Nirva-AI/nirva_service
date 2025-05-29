from db.pgsql_object import UserDB
from db.pgsql_client import SessionLocal


############################################################################################################
def save_user(
    user_name: str,
    hashed_password: str,
) -> UserDB:
    """
    保存用户到PostgreSQL数据库

    参数:
        user_name: 用户名
        hashed_password: 哈希后的密码

    返回:
        UserDB 对象
    """
    db = SessionLocal()
    try:
        user = UserDB(username=user_name, hashed_password=hashed_password)
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
