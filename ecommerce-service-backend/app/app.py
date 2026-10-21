from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api import router


openapi_tags = [
    {
        "name": "系统",
        "description": "服务可用性与基础检查接口。",
    },
    {
        "name": "用户",
        "description": "查询用户相关的订单列表和商品列表。",
    },
    {
        "name": "订单",
        "description": "订单详情、订单状态、物流信息，以及订单相关操作请求。",
    },
    {
        "name": "商品",
        "description": "商品详情查询接口。",
    },
]


app = FastAPI(
    title="ShopHelper · 电商业务服务",
    version="0.1.0",
    description="提供订单、物流、商品查询和退款申请接口，供 ShopHelper 客服调用。",
    openapi_tags=openapi_tags,
)

app.include_router(router)


@app.exception_handler(OperationalError)
async def database_unavailable(request, exc):
    return JSONResponse(status_code=503, content={
        "detail": "电商数据库连接失败，请检查 MySQL 是否启动、连接配置及初始化数据。"
    })
