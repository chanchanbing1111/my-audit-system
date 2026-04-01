from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# ✅ 关键修正：因为在同一目录下，直接使用相对导入
try:
    from .sse import router as sse_router
except ImportError:
    # 兼容某些本地运行环境
    import sse as sse_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sentient Audit System API")

# 1. 配置 CORS 域名白名单
# 注意：allow_credentials=True 时，Origins 不能为 ["*"]
origins = [
    "http://localhost:3000",
    "https://my-audit-system.vercel.app",
    "https://my-audit-system-89nrhrq1g-chanchanbing1111s-projects.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 注册路由
# 注意：保持 prefix 为 /api/v1 确保与前端直连地址匹配
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
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # 注意：如果在 src 目录下启动，模块名直接是 "main"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
