"""
Sentient Audit System - FastAPI 主入口
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1. 屏蔽可能导致输出污染的 SDK 日志
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

app = FastAPI(title="Sentient Audit System")

# 2. 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 调试阶段先放开，生产环境可填具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 导入路由
try:
    from src.sse import router as sse_router
    app.include_router(sse_router, prefix="/api/v1")
    router_status = "✅ 路由加载成功"
except Exception as e:
    router_status = f"❌ 路由加载失败: {str(e)}"

# 4. 诊断接口
@app.get("/")
async def root():
    return {"status": "running", "router": router_status}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "info": router_status}
