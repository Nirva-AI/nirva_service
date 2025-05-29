############################################################################################################
def main() -> None:

    from db.pgsql_client import reset_database
    from db.redis_client import redis_flushall
    from db.pgsql_user import save_user, has_user
    from config.fake_user_account import fake_user_account
    from loguru import logger

    # 清空 Redis 数据库
    redis_flushall()

    # 清空 PostgreSQL 数据库
    reset_database()

    # 检查并保存测试用户
    if not has_user(fake_user_account.username):
        save_user(
            username=fake_user_account.username,
            hashed_password=fake_user_account.hashed_password,
        )
        logger.warning(f"测试用户 {fake_user_account.username} 已创建")


############################################################################################################
if __name__ == "__main__":
    main()
