from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from db.crypt_context import verify_password
from db.jwt import (
    create_access_token,
    create_refresh_token,
    Token,
    decode_jwt,
)
from datetime import timedelta
from config.configuration import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
import db.pgsql_user
from typing import Optional
from jose import JWTError
import db.redis_user


###################################################################################################################################################################
login_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@login_router.post(path="/login/v1/", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:

    try:

        # 检查用户是否存在
        if not db.pgsql_user.has_user(form_data.username):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 获取用户信息
        user_db = db.pgsql_user.get_user(form_data.username)
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 验证密码
        if not verify_password(form_data.password, user_db.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 生成访问令牌和刷新令牌
        access_token = create_access_token(
            data={"sub": user_db.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        refresh_token = create_refresh_token(
            data={"sub": user_db.username},
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )

        # 返回令牌
        ret = Token(
            access_token=access_token, token_type="bearer", refresh_token=refresh_token
        )

        # 将令牌存储到 Redis 中
        db.redis_user.assign_user_token(
            user_name=user_db.username,
            token=ret,
        )

        # 正确的返回。
        return ret

    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################


@login_router.post(path="/refresh/v1/", response_model=Token)
async def refresh(refresh_token: str) -> Token:

    try:

        payload = decode_jwt(refresh_token)

        username: Optional[str] = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查用户是否存在
        if not db.pgsql_user.has_user(username):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 生成新的访问令牌和刷新令牌
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        new_refresh_token = create_refresh_token(
            data={"sub": username},
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )

        # 返回新的令牌
        ret = Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=new_refresh_token,
        )

        # 更新 Redis 中的令牌
        db.redis_user.assign_user_token(
            user_name=username,
            token=ret,
        )

        return ret

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
