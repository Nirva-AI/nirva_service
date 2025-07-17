import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import Dict
import httpx
from datetime import datetime


# 创建FastAPI应用实例
app = FastAPI(title="Simple FastAPI Sample", version="1.0.0")


# 定义POST请求的数据模型
class Item(BaseModel):
    name: str
    description: str | None = None


# 定义转发请求的数据模型
class ForwardRequest(BaseModel):
    text: str


# 1. 根路径方法
@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Welcome to Simple FastAPI Sample!"}


# 2. GET方法示例
@app.get("/hello/{name}")
async def say_hello(name: str) -> Dict[str, str]:
    return {"message": f"Hello, {name}!"}


# 3. POST方法示例
@app.post("/submit")
async def submit_item(item: Item) -> Dict[str, str | Dict[str, str | None]]:
    return {
        "message": "Item received successfully!",
        "received_data": {"name": item.name, "description": item.description},
    }


# 4. 转发到内部服务的POST方法
@app.post("/forward-to-internal")
async def forward_to_internal(request: ForwardRequest) -> Dict[str, str]:
    # 添加时间戳并转发给内部服务
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    internal_payload = {"text": request.text, "timestamp": current_time}

    # 调用内部服务
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8100/process", json=internal_payload, timeout=10.0
            )
            response.raise_for_status()
            internal_result = response.json()

            # 返回处理结果给网页
            return {
                "result": internal_result["processed_text"],
                "processed_by": "internal_service",
                "timestamp": internal_result["timestamp"],
                "processed_at": internal_result["processed_at"],
            }

        except httpx.RequestError as e:
            return {
                "error": "Failed to connect to internal service",
                "details": str(e),
                "timestamp": current_time,
            }
        except httpx.HTTPStatusError as e:
            return {
                "error": "Internal service returned error",
                "status_code": str(e.response.status_code),
                "timestamp": current_time,
            }


# 运行配置
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

