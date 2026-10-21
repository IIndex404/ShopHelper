from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from atguigu.infrastructure import database, http_client
from atguigu.api.routers.chat_router import router

@asynccontextmanager
async def lifespan(app):
    database.init_db_engine()
    http_client.init_http_client()
    yield
    await http_client.close_http_client()
    await database.close_db_engine()

app = FastAPI(title="ShopHelper · 智能客服服务", lifespan=lifespan)
app.include_router(router)

@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "客服数据库连接失败，请检查 MySQL 和连接配置。"})

@app.get('/health')
async def health():
    async with database.async_session() as session:
        await session.execute(text('SELECT 1'))
    return {"status": "ok"}
