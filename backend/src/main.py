from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from src.sse import router as sse_router # 确保路径指向正确

app = FastAPI(title="Sentient Audit System API")

# 1. 定义允许跨域的源
# 建议包含本地开发环境和你的 Vercel 生产环境地址
origins = [
    "http://localhost:3000",          # Next.js 默认开发端口
    "https://my-audit-system.vercel.app", # 替换为你的 Vercel 实际访问域名
    "*"                                # 临时保留通配符以确保连通性
]

# 2. 统一配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法 (GET, POST 等)
    allow_headers=["*"],  # 允许所有请求头
)

# 3. 注册路由
# 确保你的 sse_router 导入路径与项目结构一致
app.include_router(sse_router, prefix="/api/v1", tags=["audit"])

@app.get("/")
async def root():
    # 增加一个环境检测，方便你在浏览器访问根目录时确认后端版本
    return {
        "message": "Audit System API is running",
        "mode": "Direct-to-Railway",
        "status": "Ready"
    }
