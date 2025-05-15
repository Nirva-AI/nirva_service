from sqlalchemy import create_engine, MetaData, String, delete
from sqlalchemy.orm import (
    sessionmaker,
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from passlib.context import CryptContext


# 基类定义
class Base(DeclarativeBase):
    pass


# 数据库配置
your_password = "123456"
DATABASE_URL = f"postgresql://fastapi_user:{your_password}@localhost/my_fastapi_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 密码加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 用户模型
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)


# 创建表
Base.metadata.create_all(bind=engine)


# 清库函数
def clear_database() -> None:
    meta = MetaData()
    meta.reflect(bind=engine)

    with engine.begin() as conn:
        for table in reversed(meta.sorted_tables):
            conn.execute(delete(table))


# 测试流程
def test_database_operations() -> None:
    db = SessionLocal()

    try:
        clear_database()

        test_user = User(
            username="test_user", hashed_password=pwd_context.hash("test_password")
        )

        db.add(test_user)
        db.commit()

        saved_user = db.query(User).filter_by(username="test_user").first()

        assert saved_user is not None, "数据写入失败"
        assert pwd_context.verify(
            "test_password", saved_user.hashed_password
        ), "密码验证失败"
        print("✅ 测试通过")

    finally:
        db.close()
        clear_database()
        print("🧹 数据库已清理")


if __name__ == "__main__":
    test_database_operations()


"""
psql -U fastapi_user -d my_fastapi_db
# 输入密码后执行
SELECT * FROM users;

"""
