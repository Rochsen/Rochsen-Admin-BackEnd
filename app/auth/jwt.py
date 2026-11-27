import time

import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.config import get_settings


# Payload follows RFC 7519
# https://www.rfc-editor.org/rfc/rfc7519#section-4.1
class JWTTokenPayload(BaseModel):
    iss: str
    sub: str
    exp: int
    iat: int


class JWTToken(BaseModel):
    payload: JWTTokenPayload
    access_token: str


def create_jwt_token(user_id: str) -> JWTToken:
    iat = int(time.time())
    exp = iat + get_settings().security.jwt_access_token_expire_secs

    token_payload = JWTTokenPayload(
        iss=get_settings().security.jwt_issuer,
        sub=user_id,
        exp=exp,
        iat=iat,
    )

    access_token = jwt.encode(
        token_payload.model_dump(),
        key=get_settings().security.jwt_secret_key.get_secret_value(),
        algorithm=get_settings().security.jwt_algorithm,
    )

    return JWTToken(payload=token_payload, access_token=access_token)


def verify_jwt_token(token: str) -> JWTTokenPayload:
    # 注意验证传递的 verify_signature 参数，即使它是默认值。
    # 验证是基于预期的有效载荷字段，比如 "exp"、"iat" 等。
    # 所以如果你把例如 "exp" 重命名为 "my_custom_exp"，这将会导致失败，
    # jwt.ExpiredSignatureError 将不会被抛出，这可能成为
    # 一个严重的安全风险——完全不验证令牌。
    # 如果不确定，请查看 jwt.decode 代码，确保测试通过
    # https://pyjwt.readthedocs.io/en/stable/usage.html#encoding-decoding-tokens-with-hs256

    try:
        raw_payload = jwt.decode(
            token,
            get_settings().security.jwt_secret_key.get_secret_value(),
            algorithms=[get_settings().security.jwt_algorithm],
            options={"verify_signature": True},
            issuer=get_settings().security.jwt_issuer,
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalid: {e}",
        )

    return JWTTokenPayload(**raw_payload)
