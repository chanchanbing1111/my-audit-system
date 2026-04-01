from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import sys

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 动态处理导入路径，确保在不同环境下都能找到 sse.py
try:
    from src.sse import router as sse_router
except ImportError:
    try:
        from .sse import router as sse_router
    except ImportError:
        import sse as sse_router

app = FastAPI(title="Sentient Audit System API")

# 1. 配置 CORS
# 💡 提示：如果 allow_credentials=True，origins 必须是具体列表，不能是 ["*"]
origins = [
    "http://localhost:3000",
    "https://my-audit-system.vercel.app",
    "https://my-audit-system-89nrhrq1g-chanchanbing1111s-projects.vercel.app",
    # 如果你未来换了 Vercel 账号，可以把新的 preview 域名也加在这
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # 💡 增加这一行，确保浏览器能正确处理长连接的预检请求
    expose_headers=["*"], 
)

# 2. 注册路由
app.include_router(sse_router, prefix="/api/v1", tags=["audit"])

@app.get("/")
async def root():
    return {
        "message": "Audit System API is running",
        "mode": "Direct-to-Railway",
        "status": "Ready",
        "env_check": {
            "openai_key": "Set" if os.getenv("OPENAI_API_KEY") else "Missing",
            "tavily_key": "Set" if os.getenv("TAVILY_API_KEY") else "Missing"
        },
        "python_version": sys.version
    }

if __name__ == "__main__":
    import uvicorn
    # Railway 会自动注入 PORT 环境变量
    port = int(os.environ.get("PORT", 8000))
    
    # 💡 重点：统一启动路径。如果在根目录运行，使用 "src.main:app"
    # 如果是在 src 目录下运行，使用 "main:app"
    # 这里建议根据你的 run_server.py 逻辑保持一致
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)
