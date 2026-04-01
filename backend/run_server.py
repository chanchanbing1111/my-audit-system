import uvicorn
import os
import sys

# 💡 核心修正：确保当前目录被识别为包路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # 路径必须是 "src.main:app"，因为 main.py 在 src 文件夹内
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False, 
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
