from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from db.crypt_context import verify_password
from db.jwt import (
    create_access_token,
    create_refresh_token,
    UserToken,
    decode_jwt,
)
from datetime import timedelta
from config.configuration import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
import db.pgsql_user
from typing import Optional, Dict, Any
from jose import JWTError
import db.redis_user
from app_services.oauth_user import get_authenticated_user, oauth2_scheme
import time


###################################################################################################################################################################
login_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@login_router.post(path="/login/v1/", response_model=UserToken)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> UserToken:

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
        ret = UserToken(
            access_token=access_token, token_type="bearer", refresh_token=refresh_token
        )

        # 将令牌存储到 Redis 中
        db.redis_user.assign_user_access_token(
            username=user_db.username,
            token=ret,
        )

        db.redis_user.set_user_display_name(
            username=user_db.username,
            display_name=user_db.display_name or user_db.username,
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
@login_router.post(path="/refresh/v1/", response_model=UserToken)
async def refresh(refresh_token: str = Form(...)) -> UserToken:

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
        ret = UserToken(
            access_token=access_token,
            token_type="bearer",
            refresh_token=new_refresh_token,
        )

        # 更新 Redis 中的令牌
        db.redis_user.assign_user_access_token(
            username=username,
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
@login_router.post(path="/logout/v1/")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: str = Depends(get_authenticated_user),
) -> Dict[str, Any]:
    """
    使当前用户的令牌失效，执行登出操作

    此操作将：
    1. 验证当前用户已经认证
    2. 从令牌中提取唯一标识符(jti)
    3. 将令牌添加到黑名单中，使其立即失效
    4. 响应登出成功信息
    """
    try:
        # 解析令牌内容
        payload = decode_jwt(token)

        # 处理JWT中有jti的情况 - 将令牌加入黑名单
        if "jti" in payload:
            jti = payload.get("jti")

            # 计算令牌的剩余有效时间
            exp_timestamp = payload.get("exp", 0)
            current_timestamp = time.time()
            remaining_time = max(1, int(exp_timestamp - current_timestamp))

            # 将令牌添加到黑名单
            db.redis_user.add_access_token_to_blacklist(str(jti), remaining_time)

        # 选择性操作：删除用户在Redis中的令牌信息（使所有设备登出）
        # 取消注释下面的代码以启用此功能
        db.redis_user.remove_user_access_token(current_user)

        # 返回成功响应
        return {
            "status": "success",
            "message": "用户已成功登出",
            "username": current_user,
        }

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"无效的令牌: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登出处理过程中发生错误: {str(e)}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
