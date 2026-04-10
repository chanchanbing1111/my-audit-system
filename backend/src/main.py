"""
Sentient Audit System - FastAPI 主入口 (集成真实行情接口)
"""
import os
import logging
import asyncio
import yfinance as yf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1. 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 屏蔽可能导致输出污染的 SDK 日志
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

app = FastAPI(title="Sentient Audit System")

# 2. 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 市场行情映射配置 (对应真实证券代码)
TICKER_MAP = {
    "000001.SS": "上证指数",
    "399006.SZ": "创业板指",
    "^GSPC": "标普500",
    "^IXIC": "纳斯达克",
    "^DJI": "道琼斯",
    "^HSI": "恒生指数"
}

@app.get("/")
async def root():
    return {"status": "running", "info": "Sentient Audit System API"}

@app.get("/api/v1/market_tickers")
async def get_market_tickers():
    """获取全球市场真实收盘行情"""
    results = []
    try:
        symbols = list(TICKER_MAP.keys())
        # 在线程池中运行同步调用，防止阻塞异步主线程
        tickers = await asyncio.to_thread(yf.Tickers, " ".join(symbols))
        
        for symbol, name in TICKER_MAP.items():
            try:
                # 获取实时快照数据
                fast_info = tickers.tickers[symbol].fast_info
                current_price = fast_info.last_price
                prev_close = fast_info.previous_close
                
                # 安全计算涨跌幅
                change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0
                
                results.append({
                    "name": name,
                    "val": round(current_price, 2),
                    "change": round(change_pct, 2)
                })
            except Exception as e:
                logger.error(f"解析 {symbol} 出错: {e}")
                continue
    except Exception as e:
        logger.error(f"行情接口异常: {e}")
        return {"status": "error", "message": str(e)}
    
    return results

# 4. 导入原有 SSE 路由
try:
    from src.sse import router as sse_router
    app.include_router(sse_router, prefix="/api/v1")
    logger.info("✅ SSE 路由加载成功")
except Exception as e:
    logger.error(f"❌ SSE 路由加载失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
