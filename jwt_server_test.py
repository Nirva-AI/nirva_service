from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

# from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Final, Optional, Dict, Any
from config.fake_user_account import fake_user_account
from db.crypt_context import verify_password

# 配置参数
SECRET_KEY: Final[str] = (
    "your-secret-key-here-please-change-it"  # 生产环境要用更复杂的密钥
)
ALGORITHM: Final[str] = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30
ENABLE_HTTPS: Final[bool] = True  # 是否使用 HTTPS，默认是 False
REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 7

# 模拟数据库中的用户数据
fake_users_db: Dict[str, Dict[str, str]] = {
    # "testuser": {
    #     "username": "testuser",
    #     "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 明文是 secret
    # }
}

fake_users_db[fake_user_account.username] = fake_user_account.model_dump()


# 数据模型
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str  # 新增字段


class User(BaseModel):
    username: str


# 加密工具
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


# 验证密码方法
# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return crypt_context.verify(plain_password, hashed_password)


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
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


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
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 用户认证
def authenticate_user(username: str, password: str) -> Optional[Dict[str, str]]:
    user = fake_users_db.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


# 获取当前用户
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exception
    return User(username=user["username"])


# 登录接口
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(days=7)  # 设置 refresh_token 的过期时间
    refresh_token = create_refresh_token(
        data={"sub": user["username"]}, expires_delta=refresh_token_expires
    )
    return Token(
        access_token=access_token, token_type="bearer", refresh_token=refresh_token
    )


@app.post("/refresh-token", response_model=Token)
async def refresh_access_token(refresh_token: str) -> Token:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的刷新令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exception

    # 生成新的 access_token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    # 生成新的 refresh_token
    refresh_token_expires = timedelta(days=7)
    new_refresh_token = create_refresh_token(
        data={"sub": username}, expires_delta=refresh_token_expires
    )
    return Token(
        access_token=access_token, token_type="bearer", refresh_token=new_refresh_token
    )


# 受保护的测试接口
@app.get("/protected-data")
async def get_protected_data(
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    return {"message": "你已成功访问受保护的数据！", "username": current_user.username}


def main() -> None:
    import uvicorn

    if ENABLE_HTTPS:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            ssl_keyfile="./localhost+3-key.pem",
            ssl_certfile="./localhost+3.pem",
        )
    else:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
        )


if __name__ == "__main__":
    main()
