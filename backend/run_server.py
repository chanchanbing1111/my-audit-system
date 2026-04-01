import os
import uvicorn

if __name__ == "__main__":
    # 1. 动态获取端口，这能解决 Railway 的连接问题
    port = int(os.getenv("PORT", 8000))
    
    # 2. ✨ 核心修改：因为 main.py 在 src 文件夹里
    # 所以路径必须写成 "src.main:app"
    app_path = "src.main:app" 

    print(f"🚀 服务器正在从 {app_path} 启动，端口: {port}")
    
    uvicorn.run(
        app_path,
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        proxy_headers=True,     # 必须开启：解决 Railway 代理导致的 SSE 断连
        forwarded_allow_ips="*" # 必须开启：允许所有来源的代理头
        timeout_keep_alive=65
    )
