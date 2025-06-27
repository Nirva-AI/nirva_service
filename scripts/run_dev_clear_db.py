import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Clear database development utility
def main() -> None:
    from loguru import logger

    from nirva_service.config.account import FAKE_USER
    from nirva_service.db.pgsql_client import reset_database
    from nirva_service.db.pgsql_journal_file import save_or_update_journal_file
    from nirva_service.db.pgsql_user import has_user, save_user
    from nirva_service.db.redis_client import redis_flushall
    from nirva_service.models import JournalFile

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

    # 模拟2个日记文件的存在
    path1 = Path("invisible/analyze_result_nirva-2025-04-19-00.txt.json")
    assert path1.exists(), f"文件 {path1} 不存在，请检查路径或文件名"

    path2 = Path("invisible/analyze_result_nirva-2025-05-09-00.txt.json")
    assert path2.exists(), f"文件 {path2} 不存在，请检查路径或文件名"

    json_content1 = path1.read_text(encoding="utf-8")
    json_content2 = path2.read_text(encoding="utf-8")

    journal_file1 = JournalFile.model_validate_json(json_content1)
    journal_file2 = JournalFile.model_validate_json(json_content2)

    # 存储一下！
    save_or_update_journal_file(
        username=journal_file1.username,
        journal_file=journal_file1,
    )

    save_or_update_journal_file(
        username=journal_file2.username,
        journal_file=journal_file2,
    )


# Main execution
if __name__ == "__main__":
    main()
