import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import Dict
from datetime import datetime


# 创建内部服务FastAPI应用实例
app = FastAPI(title="Internal Service", version="1.0.0")


# 定义内部服务接收的数据模型
class InternalRequest(BaseModel):
    text: str
    timestamp: str


# 内部服务处理方法
@app.post("/process")
async def process_text(request: InternalRequest) -> Dict[str, str]:
    # 将文本转为大写并添加处理状态
    processed_text = request.text.upper()

    return {
        "processed_text": processed_text,
        "timestamp": request.timestamp,
        "status": "processed",
        "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# 内部服务健康检查
@app.get("/")
async def internal_root() -> Dict[str, str]:
    return {"message": "Internal Service is running", "service": "internal"}


# 运行配置
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)