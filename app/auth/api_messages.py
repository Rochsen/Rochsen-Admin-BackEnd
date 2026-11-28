from typing import Any

JWT_ERROR_USER_REMOVED = "用户已删除"
PASSWORD_INVALID = "邮箱或密码错误"
REFRESH_TOKEN_NOT_FOUND = "未找到刷新令牌"
REFRESH_TOKEN_EXPIRED = "刷新令牌已过期"
REFRESH_TOKEN_ALREADY_USED = "刷新令牌已使用"
EMAIL_ADDRESS_ALREADY_USED = "无法使用此电子邮件地址"
PASSWORD_EMPTY = "密码不能为空"
USERNAME_AND_PASSWORD_REQUIRED = "用户名和密码不能为空"


UNAUTHORIZED_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "No `Authorization` access token header, token is invalid or user removed",
        "content": {
            "application/json": {
                "examples": {
                    "not authenticated": {
                        "summary": "No authorization token header",
                        "value": {"detail": "Not authenticated"},
                    },
                    "invalid token": {
                        "summary": "Token validation failed, decode failed, it may be expired or malformed",
                        "value": {"detail": "Token invalid: {detailed error msg}"},
                    },
                    "removed user": {
                        "summary": JWT_ERROR_USER_REMOVED,
                        "value": {"detail": JWT_ERROR_USER_REMOVED},
                    },
                }
            }
        },
    }
}

ACCESS_TOKEN_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Invalid email or password",
        "content": {"application/json": {"example": {"detail": PASSWORD_INVALID}}},
    },
}

REFRESH_TOKEN_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Refresh token expired or is already used",
        "content": {
            "application/json": {
                "examples": {
                    "refresh token expired": {
                        "summary": REFRESH_TOKEN_EXPIRED,
                        "value": {"detail": REFRESH_TOKEN_EXPIRED},
                    },
                    "refresh token already used": {
                        "summary": REFRESH_TOKEN_ALREADY_USED,
                        "value": {"detail": REFRESH_TOKEN_ALREADY_USED},
                    },
                }
            }
        },
    },
    404: {
        "description": "Refresh token does not exist",
        "content": {
            "application/json": {"example": {"detail": REFRESH_TOKEN_NOT_FOUND}}
        },
    },
}
