'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Search, Activity, ArrowLeft, TrendingUp, ShieldCheck, BarChart3, PieChart, Wallet } from 'lucide-react';

export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]); [cite: 200]
  const [activeTab, setActiveTab] = useState<'profit' | 'asset' | 'cash'>('profit');
  const [currentAgent, setCurrentAgent] = useState<string>('初始化...'); [cite: 200]
  
  // 实时行情状态：初始为空，由 useEffect 填充真实数据
  const [tickerData, setTickerData] = useState<any[]>([]); [cite: 201]
  
  const currentQueryRef = useRef<string>('');
  const sourceRef = useRef<EventSource | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null); [cite: 202]

  // 1. 获取后端真实行情逻辑
  const fetchMarketData = async () => {
    try {
      // 请将此处的 URL 替换为你后端实际的 API 地址
      const response = await fetch('https://my-audit-system-production.up.railway.app/api/v1/market_tickers');
      const data = await response.json();
      if (Array.isArray(data) && data.length > 0) {
        setTickerData(data);
      }
    } catch (err) {
      console.error("行情同步失败:", err);
    }
  };

  useEffect(() => {
    fetchMarketData(); // 初次加载
    const timer = setInterval(fetchMarketData, 60000); // 每 60 秒同步一次真实数据
    return () => clearInterval(timer);
  }, []);

  // 2. 自动滚动聊天记录 [cite: 203]
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 3. SSE 流式传输逻辑 [cite: 204, 212]
  useEffect(() => {
    if (stage !== 'chat' || !currentQueryRef.current) return;
    const query = currentQueryRef.current;
    const url = `https://my-audit-system-production.up.railway.app/api/v1/audit?company_name=${encodeURIComponent(query)}`;
    
    if (sourceRef.current) sourceRef.current.close();
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'log') {
          const agentName = data.content.match(/\[(.*?)\]/)?.[1] || ''; [cite: 205]
          if (agentName) setCurrentAgent(agentName);
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              return [...prev.slice(0, -1), { ...lastMsg, logs: [...(lastMsg.logs || []), data.content] }]; [cite: 205]
            }
            return prev;
          });
        }
        if (data.type === 'metrics') {
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...lastMsg, metrics: data.metrics || {}, charts: data.charts || {}, loading: false } [cite: 208]
              ];
            }
            return prev;
          });
        }
      } catch (e) { console.error('SSE 解析失败', e); }
    };

    source.addEventListener('complete', () => { source.close(); sourceRef.current = null; }); [cite: 211]
    source.onerror = () => { source.close(); sourceRef.current = null; }; [cite: 211]

    return () => { if (sourceRef.current) { sourceRef.current.close(); sourceRef.current = null; } };
  }, [stage]);

  const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return; [cite: 213]
    if (sourceRef.current) { sourceRef.current.close(); sourceRef.current = null; } [cite: 214]
    currentQueryRef.current = query;
    const msgId = Date.now();
    setMessages(prev => [
      ...prev,
      { id: msgId, role: 'user', content: query },
      { id: msgId + 1, role: 'assistant', content: query, logs: [], metrics: null, charts: {}, loading: true } [cite: 215]
    ]);
    setInputValue('');
    setStage('chat');
    setCurrentAgent('初始化...');
  };

  // --- 柱状图渲染组件 ---
  const MiniBarChart = ({ data, keys, colors, formatValue, unit = '' }: any) => {
    if (!data || data.length === 0) return <div className="h-40 flex items-center justify-center text-slate-300 text-xs">暂无数据</div>; [cite: 216]
    const maxVal = Math.max(...data.map((d: any) => Math.abs(d[keys[0]]) || 1)); [cite: 217]
    const defaultFormat = (v: number) => v >= 1000 ? `${(v / 10000).toFixed(1)}万` : v.toFixed(1); [cite: 218]

    return (
      <div className="w-full">
        <div className="w-full h-40 flex items-end justify-around border-b border-slate-100 pb-2">
          {data.map((d: any, i: number) => (
            <div key={i} className="flex flex-col items-center flex-1 group">
              <div className="flex flex-col items-center gap-0.5 mb-1">
                {keys.map((key: string, ki: number) => (
                  <div key={ki} className="text-[9px] font-black text-slate-600 leading-tight">
                    {formatValue ? formatValue(d[key]) : defaultFormat(d[key])} [cite: 219]
                  </div>
                ))}
              </div>
              <div className="flex items-end gap-1 h-32 relative">
                {keys.map((key: string, ki: number) => (
                  <div key={ki} style={{ height: `${Math.min((Math.abs(d[key]) / maxVal) * 100, 100)}%` }}
                    className={`w-4 ${colors[ki]} rounded-t-sm transition-all group-hover:opacity-80 relative`} [cite: 220]
                  />
                ))}
              </div>
              <span className="mt-2 text-[10px] font-bold text-slate-400">{d.year}年</span>
            </div>
          ))}
        </div>
        {unit && <div className="text-center text-[9px] text-slate-400 mt-1">{unit}</div>} [cite: 222]
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#FDFDFF] flex flex-col font-sans overflow-x-hidden">
      {/* 顶部实时流动行情条 */}
      <div className="w-full bg-[#0F172A] text-white py-3 border-b border-slate-800 z-50">
        <div className="flex whitespace-nowrap overflow-hidden">
          <div className="flex animate-marquee hover:[animation-play-state:paused] gap-12 px-6">
            {tickerData.length > 0 ? (
              [...tickerData, ...tickerData].map((item, i) => (
                <div key={i} className="flex items-center gap-3 text-[13px] font-medium border-r border-slate-800 pr-12">
                  <span className="opacity-50">{item.name}</span> [cite: 224]
                  <span className="font-bold tracking-wider">{item.val.toLocaleString()}</span> [cite: 224]
                  <span className={item.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                    {item.change >= 0 ? '+' : ''}{item.change}% [cite: 224]
                  </span>
                </div>
              ))
            ) : (
              <div className="text-slate-500 text-[13px] px-6">正在同步全球交易中心实时行情数据...</div>
            )}
          </div>
        </div>
      </div>

      <main className="flex-1 flex flex-col relative">
        <style jsx global>{`
          @keyframes marquee {
            0% { transform: translateX(0); } [cite: 226]
            100% { transform: translateX(-50%); } [cite: 227]
          }
          .animate-marquee {
            display: inline-flex;
            animation: marquee 40s linear infinite; [cite: 228]
          }
        `}</style>

        {stage === 'home' ? (
          <div className="w-full flex flex-col items-center pt-24 pb-20">
            {/* 核心徽章 */}
            <div className="mb-8 px-5 py-2 bg-violet-50 rounded-full border border-violet-100 flex items-center gap-2 shadow-sm shadow-violet-100/50"> [cite: 229]
              <Activity size={14} className="text-violet-500" />
              <span className="text-[12px] font-bold text-violet-600 uppercase tracking-[0.15em]">
                Multi-Agent 驱动 · 数据 100% 真实 · 全球市场覆盖 [cite: 230]
              </span>
            </div>

            {/* 标题区 */}
            <h1 className="text-7xl font-black mb-6 tracking-tight text-slate-900 text-center">
              智能财务报表分析终端 [cite: 230]
            </h1>
            <p className="text-slate-400 font-semibold mb-16 text-xl tracking-wide">
              专业级财报深度解析 · 秒级生成研报级分析 [cite: 231]
            </p>

            {/* 增强型搜索框 - 调大比例以适配原型图 */}
            <div className="w-full relative max-w-4xl mb-24 group px-6">
              <div className="absolute left-10 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-violet-500 transition-colors z-10"> [cite: 232]
                <Search size={26} />
              </div>
              <input
                className="w-full pl-20 pr-44 py-8 bg-white rounded-[2.5rem] border border-slate-100 shadow-[0_30px_70px_rgba(0,0,0,0.07)] outline-none focus:ring-4 ring-violet-500/10 focus:border-violet-200 text-2xl font-medium transition-all"
                placeholder="输入公司名称/代码，或直接提问：对比比亚迪与特斯拉的盈利能力" [cite: 232]
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
              />
              <button
                onClick={() => handleSend()}
                className="absolute right-10 top-3.5 bottom-3.5 px-14 bg-[#A594FD] hover:bg-violet-500 text-white font-black rounded-3xl transition-all shadow-xl shadow-violet-200 flex items-center justify-center text-xl tracking-widest" [cite: 234]
              >
                分析
              </button>
            </div>

            {/* 功能矩阵卡片 */}
            <div className="grid grid-cols-3 gap-8 w-full max-w-6xl mb-20 px-6">
              {[
                { icon: <Search className="text-blue-500" />, title: '智能数据检索', desc: '自动抓取最新官方财报数据，覆盖多维度财务指标' }, [cite: 235]
                { icon: <BarChart3 className="text-purple-500" />, title: '可视化图表', desc: '交互式图表展示财务趋势，直观呈现关键指标变化' }, [cite: 235]
                { icon: <Activity className="text-teal-500" />, title: '深度统计分析', desc: '基于统计模型生成专业研报，涵盖盈利、资产、现金流分析' }, [cite: 236]
              ].map((feat, i) => (
                <div key={i} className="p-10 bg-white border border-slate-50 rounded-[2.5rem] shadow-[0_10px_30px_rgba(0,0,0,0.02)] hover:shadow-xl hover:-translate-y-1 transition-all"> [cite: 236]
                  <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mb-8">{feat.icon}</div>
                  <h3 className="text-xl font-black text-slate-800 mb-3">{feat.title}</h3> [cite: 237]
                  <p className="text-slate-500 leading-relaxed font-medium">{feat.desc}</p>
                </div>
              ))}
            </div>

            {/* 快速入口 */}
            <div className="flex flex-col items-center gap-6">
              <span className="text-[11px] font-bold text-slate-300 uppercase tracking-[0.3em]">快速入口</span> [cite: 238]
              <div className="flex gap-4">
                {['2025 科技行业展望', '高 ROE 企业排名', '新能源汽车财务对比', '芯片行业盈利分析'].map(tag => (
                  <button key={tag} onClick={() => handleSend(tag)} className="px-7 py-3 bg-white border border-slate-100 rounded-2xl text-[13px] font-bold text-slate-500 hover:border-violet-200 hover:text-violet-600 transition-all shadow-sm"> [cite: 238]
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* 聊天分析界面 */
          <div className="w-full max-w-5xl h-full flex flex-col pt-10 pb-20 px-6 overflow-y-auto mx-auto"> [cite: 240]
            <div className="flex justify-between items-center mb-10">
              <button onClick={() => { if (sourceRef.current) sourceRef.current.close(); setStage('home'); }} className="flex items-center text-slate-400 font-bold hover:text-slate-600"> [cite: 240]
                <ArrowLeft size={20} className="mr-3" /> 返回首页
              </button>
              <div className="bg-violet-50 px-5 py-2.5 rounded-full border border-violet-100 flex items-center gap-3">
                <Activity size={16} className="text-violet-500 animate-pulse" />
                <span className="text-[12px] font-black text-violet-600 uppercase">当前节点: {currentAgent}</span> [cite: 242]
              </div>
            </div>

            <div className="space-y-8">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="p-10 rounded-[2.5rem] bg-white border border-slate-100 shadow-2xl shadow-slate-200/50 max-w-[95%] w-full"> [cite: 243]
                    {msg.role === 'assistant' && msg.metrics ? (
                      <div>
                        <div className="grid grid-cols-3 gap-6 mb-8">
                          <div className="bg-violet-600 p-6 rounded-3xl text-white shadow-xl shadow-violet-200"> [cite: 244]
                            <div className="text-[11px] font-bold opacity-70 uppercase mb-2">综合审计评分</div>
                            <div className="text-5xl font-black">{msg.metrics.score ?? '—'}</div> [cite: 245]
                          </div>
                          <div className="bg-slate-50 p-6 rounded-3xl border border-slate-100">
                            <div className="text-[11px] font-black text-slate-400 uppercase mb-2">ROE</div>
                            <div className="text-2xl font-black text-slate-900">{msg.metrics.health?.roe ?? '—'}</div> [cite: 247]
                          </div>
                          <div className="bg-slate-50 p-6 rounded-3xl border border-slate-100">
                            <div className="text-[11px] font-black text-slate-400 uppercase mb-2">最新营收</div>
                            <div className="text-2xl font-black text-slate-900">{msg.metrics.health?.latest_revenue ?? '—'}</div> [cite: 249]
                          </div>
                        </div>

                        <div className="text-[15px] font-bold text-slate-700 bg-teal-50/50 p-7 rounded-3xl border border-teal-100/50 mb-8 leading-relaxed">
                          <TrendingUp size={20} className="inline mr-3 text-teal-500" /> [cite: 250]
                          {msg.metrics.summary ?? '暂无分析结论'} [cite: 251]
                        </div>

                        <div className="bg-slate-50 p-2.5 rounded-2xl flex gap-3 mb-6"> [cite: 251]
                          {[
                            { id: 'profit', label: '盈利分析', icon: <BarChart3 size={16} /> }, [cite: 252]
                            { id: 'asset', label: '资产结构', icon: <PieChart size={16} /> }, [cite: 252]
                            { id: 'cash', label: '现金流', icon: <Wallet size={16} /> } [cite: 252]
                          ].map(tab => (
                            <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
                              className={`flex-1 flex items-center justify-center gap-3 py-3.5 text-[12px] font-bold rounded-xl transition-all ${
                                activeTab === tab.id ? 'bg-white shadow-sm text-violet-600' : 'text-slate-400 hover:bg-slate-100' [cite: 254]
                              }`}
                            >
                              {tab.icon} {tab.label} [cite: 255]
                            </button>
                          ))}
                        </div>

                        <div className="p-8 bg-white rounded-3xl border border-slate-100">
                          {activeTab === 'profit' && <MiniBarChart data={msg.charts?.profit_chart || []} keys={['revenue', 'profit']} colors={['bg-violet-500', 'bg-teal-400']} formatValue={(v: any) => `${v}亿`} unit="单位：亿元" />} [cite: 257]
                          {activeTab === 'asset' && <MiniBarChart data={msg.charts?.asset_chart || []} keys={['assets', 'debt']} colors={['bg-blue-500', 'bg-orange-400']} formatValue={(v: any) => `${v}亿`} unit="单位：亿元" />} [cite: 258]
                          {activeTab === 'cash' && <MiniBarChart data={msg.charts?.cash_chart || []} keys={['cash_flow']} colors={['bg-emerald-500']} formatValue={(v: any) => `${v}亿`} unit="单位：亿元" />} [cite: 259]
                          
                          <div className="mt-8 flex gap-8 justify-center border-t border-slate-50 pt-6"> [cite: 259]
                            {activeTab === 'profit' && (
                              <>
                                <div className="flex items-center gap-3 text-[11px] font-bold text-slate-400"><div className="w-3 h-3 bg-violet-500 rounded-full" /> 营业收入</div> [cite: 260]
                                <div className="flex items-center gap-3 text-[11px] font-bold text-slate-400"><div className="w-3 h-3 bg-teal-400 rounded-full" /> 净利润</div> [cite: 261]
                              </>
                            )}
                            {activeTab === 'asset' && (
                              <>
                                <div className="flex items-center gap-3 text-[11px] font-bold text-slate-400"><div className="w-3 h-3 bg-blue-500 rounded-full" /> 总资产</div> [cite: 262]
                                <div className="flex items-center gap-3 text-[11px] font-bold text-slate-400"><div className="w-3 h-3 bg-orange-400 rounded-full" /> 总负债</div> [cite: 263]
                              </>
                            )}
                            {activeTab === 'cash' && (
                              <div className="flex items-center gap-3 text-[11px] font-bold text-slate-400"><div className="w-3 h-3 bg-emerald-500 rounded-full" /> 经营现金流</div> [cite: 264]
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-4"> [cite: 266]
                        {msg.logs?.map((log: string, i: number) => (
                          <div key={i} className="text-[13px] text-slate-400 flex items-center font-semibold"> [cite: 266]
                            <span className="w-2 h-2 bg-violet-300 rounded-full mr-4" /> {log} [cite: 266]
                          </div>
                        ))}
                        {msg.loading && (
                          <div className="text-base text-violet-500 font-black animate-pulse mt-8 flex items-center gap-3"> [cite: 268]
                            <Activity size={20} /> 正在穿透底层账目，进行多维勾联侦测... [cite: 268]
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={scrollRef} className="h-20" /> [cite: 270]
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
