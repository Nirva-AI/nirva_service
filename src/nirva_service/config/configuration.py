from pathlib import Path
from typing import Final, final

from pydantic import BaseModel

"""
先都配置到这里写死了，简单点。
"""


##################################################################################################################
# 启动一个服务的配置
@final
class AppserviceServerConfig(BaseModel):
    server_ip_address: str = "0.0.0.0"
    server_port: int = 8001
    local_network_ip: str = "192.168.192.105"


##################################################################################################################
# 启动一个服务的配置
@final
class ChatServerConfig(BaseModel):
    port: int = 8500
    temperature: float = 0.7
    chat_service_api: str = "/chat/v1/"
    test_get_api: str = "/chat/test/get/v1/"
    fast_api_title: str = "chat_service"
    fast_api_version: str = "0.0.1"
    fast_api_description: str = ""


##################################################################################################################
# 启动一个服务的配置
@final
class AnalyzerServerConfig(BaseModel):
    port: int = 8600
    temperature: float = 0.7
    analyze_service_api: str = "/analyze/v1/"
    test_get_api: str = "/analyze/test/get/v1/"
    fast_api_title: str = "analyzer_service"
    fast_api_version: str = "0.0.1"
    fast_api_description: str = ""


##################################################################################################################
# redis的配置
@final
class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0


##################################################################################################################


# 生成log的目录
LOGS_DIR: Path = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
assert LOGS_DIR.exists(), f"找不到目录: {LOGS_DIR}"

# 根目录
GEN_CONFIGS_DIR: Path = Path("gen_configs")
GEN_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
assert GEN_CONFIGS_DIR.exists(), f"找不到目录: {GEN_CONFIGS_DIR}"


# 生成配置文件, 写死先
LLM_SERVER_CONFIG_PATH = GEN_CONFIGS_DIR / "llm_server_config.json"
llm_server_config = ChatServerConfig()
LLM_SERVER_CONFIG_PATH.write_text(
    llm_server_config.model_dump_json(),
    encoding="utf-8",
)

# 生成配置文件, 写死先
USER_SESSION_SERVER_CONFIG_PATH = GEN_CONFIGS_DIR / "user_session_server_config.json"
user_session_server_config = AppserviceServerConfig()
USER_SESSION_SERVER_CONFIG_PATH.write_text(
    user_session_server_config.model_dump_json(),
    encoding="utf-8",
)

# 生成RedisConfig配置文件，写死先
REDIS_CONFIG_PATH = GEN_CONFIGS_DIR / "redis_config.json"
redis_config = RedisConfig()
REDIS_CONFIG_PATH.write_text(
    redis_config.model_dump_json(),
    encoding="utf-8",
)

# mkcert 根证书路径, 后续可以改成环境变量
MKCERT_ROOT_CA: Final[
    str
] = r"/Users/yanghang/Library/Application Support/mkcert/rootCA.pem"

# 是否使用 HTTPS，默认是 False
LOCAL_HTTPS_ENABLED: Final[bool] = False  # 是否模拟使用 HTTPS，默认是 False

# JWT 相关配置
JWT_SIGNING_KEY: Final[str] = "your-secret-key-here-please-change-it"  # 生产环境要用更复杂的密钥
JWT_SIGNING_ALGORITHM: Final[str] = "HS256"
REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 7
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30  # 访问令牌的过期时间，单位为分钟


# 数据库配置
postgres_password: Final[str] = "123456"
POSTGRES_DATABASE_URL: Final[
    str
] = f"postgresql://fastapi_user:{postgres_password}@localhost/my_fastapi_db"


"""
psql -U fastapi_user -d my_fastapi_db
# 输入密码后执行
SELECT * FROM users;
"""
