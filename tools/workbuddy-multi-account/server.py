"""
WorkBuddy 多账号管理工具 - FastAPI 后端服务器
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from models import init_db
from api import accounts, checkin, chat
from services.scheduler import start_scheduler, stop_scheduler

# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    print("数据库初始化完成")

    # 启动定时任务调度器
    start_scheduler()

    yield
    # 关闭时清理资源
    stop_scheduler()
    print("服务器关闭")

# 创建 FastAPI 应用
app = FastAPI(
    title="WorkBuddy 多账号管理工具",
    description="支持多账号管理、自动签到、聊天记录合并与迁移",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(accounts.router)
app.include_router(checkin.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "WorkBuddy 多账号管理工具 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发环境启用热重载
        log_level="info"
    )
