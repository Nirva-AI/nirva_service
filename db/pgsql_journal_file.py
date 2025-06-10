from db.pgsql_object import JournalFileDB
from db.pgsql_client import SessionLocal
from models_v_0_0_1 import JournalFile
from .pgsql_user import get_user
from typing import List, Optional


############################################################################################################
def save_journal_file(username: str, journal_file: JournalFile) -> JournalFileDB:
    """
    保存用户的日记数据到PostgreSQL数据库

    参数:
        username: 用户名
        journal_file: JournalFile模型对象，包含日记内容

    返回:
        JournalFileDB 对象，包含创建时间和更新时间
    """
    db = SessionLocal()
    try:

        userdb = get_user(username)
        if not userdb:
            raise ValueError(f"用户 {username} 不存在")

        journal_file_db = JournalFileDB(
            user_id=userdb.id,
            username=username,
            time_stamp=journal_file.time_stamp,
            content_json=journal_file.model_dump_json(),
            # created_at 和 updated_at 会自动处理
        )
        db.add(journal_file_db)
        db.commit()
        db.refresh(journal_file_db)
        return journal_file_db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


############################################################################################################
def get_journal_file(username: str, time_stamp: str) -> Optional[JournalFileDB]:
    """
    从PostgreSQL数据库获取用户的日记数据

    参数:
        username: 用户名
        time_stamp: 日期时间戳

    返回:
        JournalFileDB 对象，如果不存在则返回None
    """
    db = SessionLocal()
    try:
        journal_file_db = (
            db.query(JournalFileDB)
            .filter_by(username=username, time_stamp=time_stamp)
            .first()
        )
        return journal_file_db
    finally:
        db.close()


############################################################################################################
def has_journal_file(username: str, time_stamp: str) -> bool:
    """
    检查用户的日记数据是否存在于PostgreSQL数据库中

    参数:
        username: 用户名
        time_stamp: 日期时间戳

    返回:
        bool: 如果日记数据存在返回True，否则返回False
    """
    db = SessionLocal()
    try:
        journal_file_exists = (
            db.query(JournalFileDB)
            .filter_by(username=username, time_stamp=time_stamp)
            .first()
            is not None
        )
        return journal_file_exists
    finally:
        db.close()


############################################################################################################
def delete_journal_file(username: str, time_stamp: str) -> bool:
    """
    删除用户的日记数据

    参数:
        username: 用户名
        time_stamp: 日期时间戳

    返回:
        bool: 如果删除成功返回True，否则返回False
    """
    db = SessionLocal()
    try:
        journal_file_db = (
            db.query(JournalFileDB)
            .filter_by(username=username, time_stamp=time_stamp)
            .first()
        )
        if journal_file_db:
            db.delete(journal_file_db)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


############################################################################################################
def journal_file_db_to_model(journal_file_db: JournalFileDB) -> JournalFile:
    """将数据库对象转换为模型对象"""
    return JournalFile.model_validate_json(journal_file_db.content_json)


############################################################################################################
def get_user_journal_files(username: str) -> List[JournalFileDB]:
    """获取用户的所有日记"""
    db = SessionLocal()
    try:
        return db.query(JournalFileDB).filter_by(username=username).all()
    finally:
        db.close()


############################################################################################################
def update_journal_file(
    username: str, journal_file: JournalFile
) -> Optional[JournalFileDB]:
    """更新现有日记内容"""
    db = SessionLocal()
    try:
        journal_file_db = (
            db.query(JournalFileDB)
            .filter_by(username=username, time_stamp=journal_file.time_stamp)
            .first()
        )
        if journal_file_db:
            journal_file_db.content_json = journal_file.model_dump_json()
            db.commit()
            db.refresh(journal_file_db)
            return journal_file_db
        return None
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


############################################################################################################
def save_or_update_journal_file(
    username: str, journal_file: JournalFile
) -> Optional[JournalFileDB]:
    """保存或更新日记"""
    existing = get_journal_file(username, journal_file.time_stamp)
    if existing:
        return update_journal_file(username, journal_file)
    else:
        return save_journal_file(username, journal_file)


############################################################################################################
