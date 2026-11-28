import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import api_messages, dependencies
from app.auth.jwt import create_jwt_token
from app.auth.models import RefreshToken, User
from app.auth.password import (
    DUMMY_PASSWORD,
    get_password_hash,
    verify_password,
)
from app.auth.schemas import (
    AccessTokenResponse,
    RefreshTokenRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdatePasswordRequest,
    VbenLoginData,
    VbenLoginRequest,
)
from app.core.api_response import ApiResult
from app.core.config import get_settings
from app.core.database_session import new_async_session

# 与 Vben 演示页按钮权限码一致，当前账号统一按超级管理员返回
VBEN_ACCESS_CODES = ["AC_100100", "AC_100110", "AC_100120", "AC_100010"]

router = APIRouter(responses=api_messages.UNAUTHORIZED_RESPONSES)


@router.get("/me", response_model=UserResponse, description="获取当前用户")
async def read_current_user(
    current_user: User = Depends(dependencies.get_current_user),
) -> User:
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    description="删除当前用户",
)
async def delete_current_user(
    current_user: User = Depends(dependencies.get_current_user),
    session: AsyncSession = Depends(new_async_session),
) -> None:
    await session.execute(delete(User).where(User.user_id == current_user.user_id))
    await session.commit()


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    description="更新当前用户密码",
)
async def reset_current_user_password(
    user_update_password: UserUpdatePasswordRequest,
    session: AsyncSession = Depends(new_async_session),
    current_user: User = Depends(dependencies.get_current_user),
) -> None:
    current_user.hashed_password = get_password_hash(user_update_password.password)
    session.add(current_user)
    await session.commit()


@router.post(
    "/access-token",
    response_model=AccessTokenResponse,
    responses=api_messages.ACCESS_TOKEN_RESPONSES,
    description="兼容 OAuth2 的令牌，使用用户名和密码获取用于未来请求的访问令牌",
)
async def login_access_token(
    session: AsyncSession = Depends(new_async_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> AccessTokenResponse:
    user = await session.scalar(select(User).where(User.email == form_data.username))

    if user is None:
        # 这是一个不提前返回的天真方法
        verify_password(form_data.password, DUMMY_PASSWORD)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_INVALID,
        )

    jwt_token = create_jwt_token(user_id=user.user_id)

    refresh_token = RefreshToken(
        user_id=user.user_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.jwt_refresh_token_expire_secs),
    )
    session.add(refresh_token)
    await session.commit()

    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token.refresh_token,
        refresh_token_expires_at=refresh_token.exp,
    )


@router.post(
    "/refresh-token",
    response_model=AccessTokenResponse,
    responses=api_messages.REFRESH_TOKEN_RESPONSES,
    description="兼容 OAuth2 的令牌，使用刷新令牌获取未来请求的访问令牌",
)
async def refresh_token(
    data: RefreshTokenRequest,
    session: AsyncSession = Depends(new_async_session),
) -> AccessTokenResponse:
    token = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.refresh_token == data.refresh_token)
        .with_for_update(skip_locked=True)
    )

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.REFRESH_TOKEN_NOT_FOUND,
        )
    elif time.time() > token.exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_EXPIRED,
        )
    elif token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_ALREADY_USED,
        )

    token.used = True
    session.add(token)

    jwt_token = create_jwt_token(user_id=token.user_id)

    refresh_token = RefreshToken(
        user_id=token.user_id,
        refresh_token=secrets.token_urlsafe(32),
        exp=int(time.time() + get_settings().security.jwt_refresh_token_expire_secs),
    )
    session.add(refresh_token)
    await session.commit()

    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token.refresh_token,
        refresh_token_expires_at=refresh_token.exp,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    description="创建新用户",
    status_code=status.HTTP_201_CREATED,
)
async def register_new_user(
    new_user: UserCreateRequest,
    session: AsyncSession = Depends(new_async_session),
) -> User:
    if new_user.password.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.PASSWORD_EMPTY,
        )
    user = await session.scalar(select(User).where(User.email == new_user.email))
    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    user = User(
        email=new_user.email,
        hashed_password=get_password_hash(new_user.password),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:  # pragma: no cover
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        )

    return user


def vben_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": -1,
            "data": None,
            "message": message,
        },
    )


@router.post(
    "/login",
    response_model=ApiResult[VbenLoginData],
    description="Vben 登录，请求体为用户名和密码，成功时返回 accessToken",
)
async def login(
    data: VbenLoginRequest,
    session: AsyncSession = Depends(new_async_session),
) -> ApiResult[VbenLoginData] | JSONResponse:
    if data.username.strip() == "" or data.password.strip() == "":
        return vben_error(
            api_messages.USERNAME_AND_PASSWORD_REQUIRED,
            status.HTTP_400_BAD_REQUEST,
        )

    user = await session.scalar(select(User).where(User.email == data.username))
    if user is None:
        verify_password(data.password, DUMMY_PASSWORD)
        return vben_error(api_messages.PASSWORD_INVALID, status.HTTP_403_FORBIDDEN)

    if not verify_password(data.password, user.hashed_password):
        return vben_error(api_messages.PASSWORD_INVALID, status.HTTP_403_FORBIDDEN)

    jwt_token = create_jwt_token(user_id=user.user_id)
    return ApiResult(data=VbenLoginData(accessToken=jwt_token.access_token))


@router.get(
    "/codes",
    response_model=ApiResult[list[str]],
    description="获取当前用户权限码",
)
async def read_access_codes(
    _: User = Depends(dependencies.get_current_user),
) -> ApiResult[list[str]]:
    return ApiResult(data=VBEN_ACCESS_CODES)


@router.post(
    "/logout", response_model=ApiResult[str], description="退出登录状态，返回登录界面"
)
async def logout() -> ApiResult[str]:
    return ApiResult(data="")
