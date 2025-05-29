############################################################################################################
def main() -> None:

    from db.pgsql_client import clear_database
    from db.redis_client import redis_flushall

    # 清空 Redis 数据库
    redis_flushall()

    # 清空 PostgreSQL 数据库
    clear_database()


############################################################################################################
if __name__ == "__main__":
    main()
