from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Final, Optional, Dict, Any

############################################################################################################
# 配置参数
SECRET_KEY: Final[str] = (
    "your-secret-key-here-please-change-it"  # 生产环境要用更复杂的密钥
)
ALGORITHM: Final[str] = "HS256"
REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 7


############################################################################################################
# 数据模型
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str  # 新增字段


############################################################################################################
# 创建JWT令牌
def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = _encode_jwt(to_encode)
    return encoded_jwt


############################################################################################################
def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )  # 默认 7 天有效期
    to_encode.update({"exp": expire})
    encoded_jwt = _encode_jwt(to_encode)
    return encoded_jwt


############################################################################################################
def _encode_jwt(
    to_encode: dict[str, Any],
) -> str:
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"JWT 编码失败: {e}")
        return ""


############################################################################################################
def decode_jwt(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except JWTError:
        return {}


############################################################################################################
