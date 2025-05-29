from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional
from db.jwt import (
    decode_jwt,
)
from db.pgsql_object import UserDB
import db.pgsql_user

# 获取当前用户
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_authenticated_user(token: str = Depends(oauth2_scheme)) -> UserDB:

    try:
        payload = decode_jwt(token)
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查用户是否存在
        if not db.pgsql_user.has_user(username):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 获取用户信息
        user_db = db.pgsql_user.get_user(username)
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        return user_db

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
