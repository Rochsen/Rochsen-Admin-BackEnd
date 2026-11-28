from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import VbenUserInfo
from app.core.api_response import ApiResult

router = APIRouter()

# 当前用户表没有角色字段，登录后按超级管理员放行前端路由
DEFAULT_ROLES = ["super"]
DEFAULT_HOME_PATH = "/dashboard/workspace"


@router.get(
    "/info", response_model=ApiResult[VbenUserInfo], description="获取当前用户信息"
)
async def read_user_info(
    current_user: User = Depends(get_current_user),
) -> ApiResult[VbenUserInfo]:
    email_name = current_user.email.split("@", maxsplit=1)[0]
    return ApiResult(
        data=VbenUserInfo(
            userId=current_user.user_id,
            username=current_user.email,
            realName=email_name,
            roles=DEFAULT_ROLES,
            avatar="",
            homePath=DEFAULT_HOME_PATH,
            desc="",
        )
    )
