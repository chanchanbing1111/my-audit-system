import os
import uvicorn

if __name__ == "__main__":
    # 强制设置 API Key 防止丢失
    os.environ['TAVILY_API_KEY'] = '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'
    
    # 使用字符串 "src.main:app" 启动，这是避免全家桶式导入报错的最佳方案
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False, # 生产环境关闭 reload
        log_level="info"
    )
