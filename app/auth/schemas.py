from pydantic import BaseModel, ConfigDict, EmailStr


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserUpdatePasswordRequest(BaseModel):
    password: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    token_type: str = "Bearer"
    access_token: str
    expires_at: int
    refresh_token: str
    refresh_token_expires_at: int

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class VbenLoginRequest(BaseModel):
    username: str
    password: str


class VbenLoginData(BaseModel):
    # 字段名与 Vben 前端 LoginResult 一致
    accessToken: str


class VbenUserInfo(BaseModel):
    # 字段名与 Vben 前端 UserInfo 一致
    userId: str
    username: str
    realName: str
    roles: list[str]
    avatar: str
    homePath: str
    desc: str
