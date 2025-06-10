import json
from typing import Dict, Any, Optional, final
from enum import StrEnum, unique
from datetime import datetime
import db.redis_client


###############################################################################################################################################
@final
@unique
class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


###############################################################################################################################################
def create_task(username: str, task_type: str) -> str:
    """创建一个新任务并返回任务ID"""

    import uuid

    task_id = str(uuid.uuid4())

    # 存储任务信息
    task_key = f"task:{username}:{task_id}"
    task_data = {
        "status": TaskStatus.PENDING,
        "task_type": task_type,
        "created_at": json.dumps(datetime.now(), default=str),
        "result": "",  # 确保是字符串而非 None
        "error": "",  # 确保是字符串而非 None
    }

    db.redis_client.redis_hmset(task_key, task_data)

    # 设置过期时间(7天)
    db.redis_client.redis_expire(task_key, seconds=60 * 60 * 24 * 7)

    return task_id


###############################################################################################################################################
def update_task_status(
    username: str,
    task_id: str,
    status: TaskStatus,
    result: Any = None,
    error: Optional[str] = None,
) -> None:
    """更新任务状态"""

    task_key = f"task:{username}:{task_id}"

    # status 已经是 TaskStatus 类型，不需要修改
    updates: Dict[str, Any] = {"status": status}

    if result is not None:
        updates["result"] = json.dumps(result)

    if error is not None:
        updates["error"] = error

    db.redis_client.redis_hmset(task_key, updates)


###############################################################################################################################################
def get_task_status(username: str, task_id: str) -> Dict[str, Any] | None:
    """获取任务状态和结果"""

    task_key = f"task:{username}:{task_id}"

    task_data = db.redis_client.redis_hgetall(task_key)

    if not task_data:
        return None  # 现在返回类型是 Dict[str, Any] | None

    if "result" in task_data and task_data["result"]:
        task_data["result"] = json.loads(task_data["result"])

    return task_data


###############################################################################################################################################
