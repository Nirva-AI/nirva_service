# 引入上一级的目录
import sys
from pathlib import Path

# 添加上一级目录到系统路径
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, MetaData, delete
from sqlalchemy.orm import (
    sessionmaker,
)
from passlib.context import CryptContext
from db.postgresql_object import Base, User  # 导入User模型

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
def clear_database() -> None:
    meta = MetaData()
    meta.reflect(bind=engine)

    with engine.begin() as conn:
        for table in reversed(meta.sorted_tables):
            conn.execute(delete(table))


############################################################################################################
# 测试流程
def test_database_operations() -> None:
    db = SessionLocal()

    try:
        clear_database()

        saved_user1 = db.query(User).filter_by(username="test_user1").first()
        assert saved_user1 is None, "清库失败，test_user1 仍然存在"
        saved_user2 = db.query(User).filter_by(username="test_user2").first()
        assert saved_user2 is None, "清库失败，test_user2 仍然存在"

        test_user1 = User(
            username="test_user1", hashed_password=pwd_context.hash("test_password1")
        )

        test_user2 = User(
            username="test_user2", hashed_password=pwd_context.hash("test_password2")
        )

        db.add(test_user1)
        db.add(test_user2)
        db.commit()

        saved_user1 = db.query(User).filter_by(username="test_user1").first()
        saved_user2 = db.query(User).filter_by(username="test_user2").first()

        assert saved_user1 is not None, "数据写入失败"
        assert pwd_context.verify(
            "test_password1", saved_user1.hashed_password
        ), "test_user1 密码验证失败"

        assert saved_user2 is not None, "数据写入失败"
        assert pwd_context.verify(
            "test_password2", saved_user2.hashed_password
        ), "test_user2 密码验证失败"

        print("✅ 测试通过")

    finally:
        db.close()
        clear_database()
        print("🧹 数据库已清理")


############################################################################################################
if __name__ == "__main__":
    test_database_operations()

############################################################################################################
# """
# psql -U fastapi_user -d my_fastapi_db
# # 输入密码后执行
# SELECT * FROM users;

# 退出是: \q
# """
