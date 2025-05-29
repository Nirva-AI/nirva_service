from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional
from db.jwt import (
    decode_jwt,
    Token,
)
import db.pgsql_user
import db.redis_user

# 获取当前用户
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_authenticated_user(token: str = Depends(oauth2_scheme)) -> str:

    try:
        payload = decode_jwt(token)
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if db.redis_user.is_user_token_present(username):
            # 如果 Redis 中存在用户令牌，直接返回用户名
            return username

        # 检查用户是否存在
        if not db.pgsql_user.has_user(username):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 获取用户信息
        user_db = db.pgsql_user.get_user(username)
        db.redis_user.assign_user_token(
            user_db.username,
            Token(
                access_token=token,
                token_type="bearer",
                refresh_token="",  # 假设没有刷新令牌
            ),
        )
        return user_db.username

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
