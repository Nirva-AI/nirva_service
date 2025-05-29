from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
)
from passlib.context import CryptContext
from db.pgsql_object import Base

############################################################################################################
# 数据库配置
your_password = "123456"
DATABASE_URL = f"postgresql://fastapi_user:{your_password}@localhost/my_fastapi_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
############################################################################################################
# 密码加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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

    print("🔄 数据库表已被清除然后重建")


############################################################################################################
