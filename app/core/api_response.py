from pydantic import BaseModel


class ApiResult[DataT](BaseModel):
    """Vben 前端约定的统一响应。code 为 0 表示成功。"""

    code: int = 0
    data: DataT
    message: str = "ok"
