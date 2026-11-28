from fastapi import status
from httpx import AsyncClient

from app.auth import api_messages
from app.auth.models import User
from app.auth.views import VBEN_ACCESS_CODES
from app.main import app
from app.tests.auth import TESTS_USER_PASSWORD
from app.user.views import DEFAULT_HOME_PATH, DEFAULT_ROLES


async def test_vben_login_returns_access_token(
    client: AsyncClient,
    default_user: User,
) -> None:
    response = await client.post(
        app.url_path_for("login"),
        json={"username": default_user.email, "password": TESTS_USER_PASSWORD},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"]["accessToken"]


async def test_vben_login_rejects_empty_username(client: AsyncClient) -> None:
    response = await client.post(
        app.url_path_for("login"),
        json={"username": "  ", "password": TESTS_USER_PASSWORD},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["message"] == api_messages.USERNAME_AND_PASSWORD_REQUIRED


async def test_vben_login_rejects_empty_password(
    client: AsyncClient,
    default_user: User,
) -> None:
    response = await client.post(
        app.url_path_for("login"),
        json={"username": default_user.email, "password": "  "},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["message"] == api_messages.USERNAME_AND_PASSWORD_REQUIRED


async def test_vben_login_rejects_unknown_user(client: AsyncClient) -> None:
    response = await client.post(
        app.url_path_for("login"),
        json={"username": "missing@example.com", "password": TESTS_USER_PASSWORD},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["message"] == api_messages.PASSWORD_INVALID


async def test_vben_login_rejects_wrong_password(
    client: AsyncClient,
    default_user: User,
) -> None:
    response = await client.post(
        app.url_path_for("login"),
        json={"username": default_user.email, "password": "wrong-password"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["message"] == api_messages.PASSWORD_INVALID


async def test_vben_user_info_and_codes(
    client: AsyncClient,
    default_user: User,
    default_user_headers: dict[str, str],
) -> None:
    info_response = await client.get(
        app.url_path_for("read_user_info"),
        headers=default_user_headers,
    )
    assert info_response.status_code == status.HTTP_200_OK
    info = info_response.json()["data"]
    assert info["userId"] == default_user.user_id
    assert info["username"] == default_user.email
    assert info["realName"] == default_user.email.split("@", maxsplit=1)[0]
    assert info["roles"] == DEFAULT_ROLES
    assert info["homePath"] == DEFAULT_HOME_PATH

    codes_response = await client.get(
        app.url_path_for("read_access_codes"),
        headers=default_user_headers,
    )
    assert codes_response.status_code == status.HTTP_200_OK
    assert codes_response.json()["data"] == VBEN_ACCESS_CODES


async def test_vben_logout(client: AsyncClient) -> None:
    response = await client.post(app.url_path_for("logout"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == 0
    assert response.json()["data"] == ""
