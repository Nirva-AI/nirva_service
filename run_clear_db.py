############################################################################################################
def main() -> None:

    from db.pgsql_client import reset_database
    from db.redis_client import redis_flushall
    from db.pgsql_user import save_user, has_user
    from config.user_account import FAKE_USER
    from loguru import logger

    # 清空 Redis 数据库
    redis_flushall()

    # 清空 PostgreSQL 数据库
    reset_database()

    # 检查并保存测试用户
    if not has_user(FAKE_USER.username):
        save_user(
            username=FAKE_USER.username,
            hashed_password=FAKE_USER.hashed_password,
            display_name=FAKE_USER.display_name,
        )
        logger.warning(f"测试用户 {FAKE_USER.username} 已创建")


############################################################################################################
if __name__ == "__main__":
    main()
