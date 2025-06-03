from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel
from typing import Final, Optional, Dict
from config.user_account import FAKE_USER
from db.crypt_context import verify_password
from db.jwt import (
    create_access_token,
    create_refresh_token,
    UserToken,
    decode_jwt,
)
from config.configuration import LOCAL_HTTPS_ENABLED

ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30

# 模拟数据库中的用户数据
fake_users_db: Dict[str, Dict[str, str]] = {}

fake_users_db[FAKE_USER.username] = FAKE_USER.model_dump()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


class User(BaseModel):
    username: str


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
        # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload = decode_jwt(token)
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
@app.post("/token", response_model=UserToken)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> UserToken:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token_expires = timedelta(days=7)  # 设置 refresh_token 的过期时间
    refresh_token = create_refresh_token(
        data={"sub": user["username"]}, expires_delta=refresh_token_expires
    )
    return UserToken(
        access_token=access_token, token_type="bearer", refresh_token=refresh_token
    )


@app.post("/refresh-token", response_model=UserToken)
async def refresh_access_token(refresh_token: str) -> UserToken:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的刷新令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        payload = decode_jwt(refresh_token)
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exception

    # 生成新的 access_token
    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # 生成新的 refresh_token
    refresh_token_expires = timedelta(days=7)
    new_refresh_token = create_refresh_token(
        data={"sub": username}, expires_delta=refresh_token_expires
    )
    return UserToken(
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

    if LOCAL_HTTPS_ENABLED:
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
