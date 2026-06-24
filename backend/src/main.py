from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from .sse import router as sse_router

app = FastAPI(title="Sentient Audit System API")

# 在这里统一配置 CORS，前端才能连上
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境可以填具体的 Vercel 地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由：注意 prefix 是 /api/v1
app.include_router(sse_router, prefix="/api/v1", tags=["audit"])

@app.get("/")
async def root():
    return {"message": "API is running"}
