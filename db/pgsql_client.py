from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
)
from db.pgsql_object import Base
from loguru import logger
from config.configuration import POSTGRES_DATABASE_URL


############################################################################################################
engine = create_engine(POSTGRES_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
############################################################################################################
# 创建表
Base.metadata.create_all(bind=engine)


############################################################################################################
# 清库函数
def reset_database() -> None:
    """
    清空数据库并重建表结构
    注意：该方法会删除所有数据，只适用于开发环境
    """
    # 删除所有现有表
    Base.metadata.drop_all(bind=engine)

    # 重新创建所有表
    Base.metadata.create_all(bind=engine)

    logger.warning("🔄 数据库表已被清除然后重建")


############################################################################################################
