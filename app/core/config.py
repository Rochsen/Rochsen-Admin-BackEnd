# 包含环境变量和通用配置逻辑的文件。
# 环境变量按嵌套组组合，例如 "Security"、"Database" 等。
# 因此，jwt_secret_key 的环境变量（不区分大小写）将是 "security__jwt_secret_key"
#
# Pydantic 优先级顺序：
#
# 1. （最重要，会覆盖所有内容）- 环境变量
# 2. 项目根文件夹中的 `.env` 文件
# 3. 默认值
#
# "sqlalchemy_database_uri" 是计算字段，将创建有效的数据库 URL
#
# 参见 https://pydantic-docs.helpmanual.io/usage/settings/
# 注意，像列表这样的复杂类型将以 JSON 编码的字符串读取。


import logging.config
from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL

PROJECT_DIR = Path(__file__).parent.parent.parent


class Security(BaseModel):
    jwt_issuer: str = "my-app"
    jwt_secret_key: SecretStr = SecretStr("hkuoviBiMxKl0rJ7X7q9nSNM1XSznDkJMdh5LMZZY7s")
    jwt_access_token_expire_secs: int = Field(default=1 * 3600, gt=10)  # 1h
    jwt_refresh_token_expire_secs: int = Field(default=28 * 24 * 3600, gt=60)  # 28d
    jwt_algorithm: str = "HS256"

    password_bcrypt_rounds: int = 12
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    backend_cors_origins: list[AnyHttpUrl] = []


class Database(BaseModel):
    hostname: str = "postgres"
    username: str = "postgres"
    password: SecretStr = SecretStr("passwd-change-me")
    port: int = 5432
    db: str = "postgres"


class Prometheus(BaseModel):
    enabled: bool = False
    port: int = 9090
    addr: str = "0.0.0.0"
    stop_delay_secs: int = 0


class Settings(BaseSettings):
    security: Security = Field(default_factory=Security)
    database: Database = Field(default_factory=Database)
    prometheus: Prometheus = Field(default_factory=Prometheus)

    log_level: str = "INFO"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.database.username,
            password=self.database.password.get_secret_value(),
            host=self.database.hostname,
            port=self.database.port,
            database=self.database.db,
        )

    model_config = SettingsConfigDict(
        env_file=f"{PROJECT_DIR}/.env",
        case_sensitive=False,
        env_nested_delimiter="__",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def logging_config(log_level: str) -> None:
    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} [{levelname}] {name}: {message}",
                "style": "{",
            },
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "level": "DEBUG",
            },
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["stream"],
                "propagate": True,
            },
        },
    }
    logging.config.dictConfig(conf)


logging_config(log_level=get_settings().log_level)
