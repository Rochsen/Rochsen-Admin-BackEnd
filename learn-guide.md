# 学习这个项目

这是一个 FastAPI + PostgreSQL 的后端模板，业务几乎都在登录鉴权上。按「先把一条请求点通，再顺着代码读」来学，不要按文件夹从头扫。

服务启动后打开 http://localhost:8000/ ，这是接口文档（`docs_url` 配在根路径 `/`）。

## 本地怎么跑

Docker 只负责数据库。本机已经有 PostgreSQL 18，监听 `5432`，直接连它即可。

`.env` 里和数据库有关的是这几项，值要和本机库一致：

```env
DATABASE__HOSTNAME=localhost
DATABASE__USERNAME=postgres
DATABASE__PASSWORD=安装 PostgreSQL 时设的密码
DATABASE__PORT=5432
DATABASE__DB=rochsen_admin_db
```

在项目根目录执行：

```powershell
uv sync
uv run alembic upgrade head
python -m app.main
```

`uv sync` 会按 `pyproject.toml` 安装 Python 3.15 和依赖。`alembic upgrade head` 把表建到 `rochsen_admin_db`。

`python -m app.main` 是按模块名运行 `app/main.py`。Python 会把当前目录（项目根目录）放进模块搜索路径，文件里的 `from app.auth.views import ...` 才能找到包 `app`。这时 `__name__` 仍是 `"__main__"`，所以文件末尾的启动代码会执行。

`python .\app\main.py` 是直接运行那个文件，搜索路径第一项变成 `app` 目录，同样的 import 会报 `No module named 'app'`。

`main.py` 末尾必须把应用写成导入字符串：

```python
run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

热重载时 uvicorn 要重新导入模块。传入 `app` 这个对象时，热重载开不起来，进程会直接退出。

## 第 1 步：把接口点一遍

在文档页按这个顺序试：

1. `POST /auth/register`：注册一个用户，请求体是邮箱和密码。
2. `POST /auth/access-token`：用邮箱当用户名、配上密码，换到 `access_token` 和 `refresh_token`。这个接口走表单，不是 JSON。
3. 点右上角 Authorize。`username` 填注册时的邮箱，`password` 填密码，`client_id` 和 `client_secret` 留空，再点 Authorize。这里没有粘贴令牌的输入框。Swagger 会自己请求 `auth/access-token`，把返回的 `access_token` 带到后面的接口上。
4. `GET /auth/me`：看当前用户。
5. `POST /auth/refresh-token`：用刷新令牌再换一对新令牌。旧的刷新令牌用过一次就不能再用。
6. `GET /probe/live`：只表示进程活着。
7. `GET /probe/health`：还会拿一次数据库会话，用来确认数据库连得上。

做完后到数据库客户端看 `auth_user` 多了一行，`auth_refresh_token` 也多了一行。

## 第 2 步：顺着这一次登录读代码

| 顺序 | 文件                                                               | 看什么                                     |
| ---- | ------------------------------------------------------------------ | ------------------------------------------ |
| 1    | `app/main.py`                                                      | 应用怎么创建，`/auth`、`/probe` 怎么挂上去 |
| 2    | `app/auth/views.py` 里的 `register_new_user`、`login_access_token` | 注册和登录                                 |
| 3    | `app/auth/schemas.py`                                              | 请求体、响应体长什么样                     |
| 4    | `app/auth/password.py`                                             | 密码怎么哈希、怎么校验                     |
| 5    | `app/auth/jwt.py`                                                  | 访问令牌怎么签发、怎么校验                 |
| 6    | `app/auth/dependencies.py`                                         | `/auth/me` 怎么从令牌找出当前用户          |
| 7    | `app/auth/models.py`                                               | `auth_user`、`auth_refresh_token` 两张表   |

登录时做两件事：

- 访问令牌是一段短期 JWT，不落库。`sub` 里放的是 `user_id`，过期时间由 `SECURITY__JWT_*` 和 `jwt_access_token_expire_secs` 决定，默认 15 分钟。
- 刷新令牌是随机字符串，写进 `auth_refresh_token`。默认 28 天，用过会被标成 `used`，再换一次会发一条新的。

所以访问令牌过期后，还能用刷新令牌换新的，也能在库里把旧刷新令牌作废。

`/auth/me` 的链路是：请求头里的 Bearer 令牌交给 `get_current_user`，`verify_jwt_token` 解出 `user_id`，再查 `auth_user`。

## 第 3 步：看数据和配置从哪来

- `app/core/config.py` 和 `.env`：`DATABASE__*`、`SECURITY__*` 用双下划线嵌进 `Settings`。优先级是环境变量，然后是 `.env`，最后是代码里的默认值。
- `app/core/database_session.py`：每个接口里的 `session` 从这里来，用完会关。`new_script_async_session` 给不经过 FastAPI 的脚本用。
- `app/core/models.py`：所有表的公共基类 `Base`。
- `app/core/lifespan.py`：进程启动时开 Prometheus（`.env` 里 `PROMETHEUS__ENABLED=true`，地址 `127.0.0.1:9090`），退出时关掉数据库连接。
- `alembic/versions/` 里的迁移文件：这些表当初是怎么建出来的。改了模型之后用 `uv run alembic revision --autogenerate -m "说明"` 生成新迁移，再用 `uv run alembic upgrade head` 应用到库。

模型里只写了 `__tablename__`，没有指定模式，所以表都在 `public` 下面。

## 第 4 步：用测试当说明书

`app/auth/tests/` 里每个文件对应一个接口，例如 `test_view_login_access_token.py`。先看测试调用了哪个地址、传了什么、期望什么状态码，再回去对 `views.py`。

跑测试：

```powershell
uv run pytest
```

测试会自己建临时库，依赖本机 PostgreSQL 能连上 `.env` 里的账号。

## 数据库里的四层

客户端左侧树从上到下是：

1. **连接**：保存的是连哪台机器、哪个端口。`localhost:5432` 是本机正在跑的 PostgreSQL。连接名可以和库名相同，这只是保存时起的名字。
2. **数据库**：真正的一份数据。应用通过 `DATABASE__DB` 进入 `rochsen_admin_db`。一次连接下面可以有很多库。
3. **模式**：库里面的分组。PostgreSQL 建库时自带 `public`。完整表名是「库.模式.表」，例如 `rochsen_admin_db.public.auth_user`。平时写 SQL 可以省略 `public`。
4. **表**：存行数据的地方。

| 表                   | 作用                                            |
| -------------------- | ----------------------------------------------- |
| `alembic_version`    | 记录迁移执行到哪一版，由 Alembic 维护，不要手改 |
| `auth_user`          | 用户账号。密码字段存的是哈希，不是明文          |
| `auth_refresh_token` | 登录后签发的刷新令牌                            |

## 读完之后

注册、登录、`/auth/me` 这三条链路清楚之后，再加自己的接口。新功能按同样的切法放：`models.py` 定义表，`schemas.py` 定义请求和响应，`views.py` 写接口，然后在 `main.py` 里 `include_router`。表结构有变化时补一条 Alembic 迁移。
