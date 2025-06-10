from typing import Optional
import db.redis_client

# Redis 存储大型 JSON 数据的考虑因素
# Redis 确实可以用于存储较大的 JSON 文件或字符串，但有一些重要的考虑因素：

# 技术上可行
# Redis 字符串值的最大大小为 512MB
# 可以使用 SET 命令直接存储 JSON 字符串
# 需要注意的限制
# 内存消耗

# Redis 是内存数据库，大型 JSON 会占用同等大小的内存
# 内存溢出风险需要考虑
# 性能影响

# 处理大型字符串会影响 Redis 的性能
# 读取/写入大型 JSON 可能导致阻塞
# 网络带宽

# 传输大型 JSON 会消耗大量网络资源
# 适合场景

# 临时缓存中等大小的 JSON (几MB)
# 有合理过期时间的数据
# 读多写少的场景
# 替代方案
# 如果 JSON 非常大（如数十或数百 MB），可以考虑：

# 分片存储：将大型 JSON 拆分成多个小块存储

# 使用 Redis Hash：如果是结构化数据，可以转换为 Hash 存储，便于部分更新

# 文件系统+Redis 索引：

# 存储大型 JSON
# import json
# import os

# # 将大型JSON保存到文件系统
# def save_large_json(data_id, json_data):
#     file_path = f"/path/to/storage/{data_id}.json"
#     with open(file_path, 'w') as f:
#         json.dump(json_data, f)
#     # 在Redis中仅存储路径
#     db.redis_client.redis_set(f"large_json:{data_id}", file_path)
#     db.redis_client.redis_expire(f"large_json:{data_id}", 3600)  # 设置过期时间

# 使用专门的文档数据库：如 MongoDB
# 根据您项目的具体需求和数据大小，选择最合适的方案。


###############################################################################################################################################
def _upload_transcript_key(username: str, time_stamp: str, file_number: int) -> str:
    return f"upload_transcript:{username}:{time_stamp}:{file_number}"


###############################################################################################################################################
# 存个几M的，就先这样，后续等必要时候再换正规的。
def store_transcript(
    username: str,
    time_stamp: str,
    file_number: int,
    transcript_content: str,
    expiration_time: Optional[int] = None,
) -> None:
    """
    存储用户的转录内容到Redis

    参数:
        username: 用户名
        time_stamp: 时间戳
        file_number: 文件编号
        transcript_content: 转录内容
        expiration_time: 可选的过期时间（秒），如果为None或小于等于0，则默认为60秒
    """
    expire_seconds = (
        expiration_time if expiration_time is not None and expiration_time > 0 else 60
    )
    upload_transcript_key = _upload_transcript_key(username, time_stamp, file_number)
    db.redis_client.redis_setex(
        upload_transcript_key, expire_seconds, transcript_content
    )


###############################################################################################################################################
def get_transcript(username: str, time_stamp: str, file_number: int) -> str:
    """
    获取用户的转录内容

    参数:
        username: 用户名
        time_stamp: 时间戳
        file_number: 文件编号

    返回:
        str: 转录内容，如果不存在则返回空字符串
    """
    upload_transcript_key = _upload_transcript_key(username, time_stamp, file_number)
    transcript_content = db.redis_client.redis_get(upload_transcript_key)
    return transcript_content if transcript_content is not None else ""


###############################################################################################################################################
def is_transcript_stored(username: str, time_stamp: str, file_number: int) -> bool:
    """
    检查用户的转录内容是否已存储

    参数:
        username: 用户名
        time_stamp: 时间戳
        file_number: 文件编号

    返回:
        bool: 如果转录内容已存储则返回True，否则返回False
    """
    upload_transcript_key = _upload_transcript_key(username, time_stamp, file_number)
    return db.redis_client.redis_exists(upload_transcript_key)


###############################################################################################################################################
def remove_transcript(username: str, time_stamp: str, file_number: int) -> None:
    """
    从Redis中删除用户的转录内容

    参数:
        username: 用户名
        time_stamp: 时间戳
        file_number: 文件编号
    """
    upload_transcript_key = _upload_transcript_key(username, time_stamp, file_number)
    db.redis_client.redis_delete(upload_transcript_key)


###############################################################################################################################################
