"use client";

import { useState } from "react";

// 定义严格的前端数据骨架
interface AnalysisResult {
  pain_points: string[];
  selling_proposals: string[];
  auto_reply_template: string;
}

export default function Home() {
  // 状态机管理
  const [status, setStatus] = useState<"idle" | "polling" | "success" | "error">("idle");
  const [inputMode, setInputMode] = useState<"url" | "query" | "none">("none");
  const [url, setUrl] = useState("");
  const [userQuery, setUserQuery] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);

  // 处理输入框互斥逻辑
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setUrl(val);
    if (val.trim() !== "") {
      setInputMode("url");
      setUserQuery(""); // 清空另一个框
    } else if (userQuery.trim() === "") {
      setInputMode("none");
    }
  };

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setUserQuery(val);
    if (val.trim() !== "") {
      setInputMode("query");
      setUrl(""); // 清空另一个框
    } else if (url.trim() === "") {
      setInputMode("none");
    }
  };

  // 模拟提交与高并发异步轮询
  // 在原有的 useState 定义区，新增一行用于存储细粒度的轮询状态信息
  const [pollingStatusMsg, setPollingStatusMsg] = useState("");

  // 模拟提交与高并发异步轮询 -> 变更为：真实的高并发异步网络轮询
  const handleStartAnalysis = async () => {
    setErrorMessage("");
    setPollingStatusMsg("");

    // 前端基础鉴权拦截
    if (!inviteCode) {
      setErrorMessage("错误：必须提供专属邀请码。");
      return;
    }
    if (inputMode === "none") {
      setErrorMessage("错误：请选择提供商品链接 (在线抓取) 或 输入分析问题 (本地 RAG)。");
      return;
    }

    setStatus("polling");
    setResult(null);

    try {
      // 步骤 1：发射任务单，获取 task_id
      setPollingStatusMsg("正在接驳网关节点，派发计算任务...");
      // 注意：请确保你的 FastAPI 后端运行在本地的 8000 端口
      const initResponse = await fetch("http://localhost:8000/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url,
          user_query: userQuery,
          invite_code: inviteCode
        }),
      });

      if (!initResponse.ok) {
        throw new Error(`网关拒绝了请求 (HTTP ${initResponse.status})`);
      }

      const initData = await initResponse.json();
      const taskId = initData.task_id;

      if (!taskId) {
        throw new Error("未能获取到任务号码牌 (Task ID)。");
      }

      // 步骤 2：启动心脏跳动式轮询 (每隔 2 秒查询一次)
      let isTaskComplete = false;
      while (!isTaskComplete) {
        setPollingStatusMsg(`[任务ID: ${taskId.substring(0, 8)}...] 正在监听 Celery 后台状态...`);

        // 发送查询请求
        const statusResponse = await fetch(`http://localhost:8000/api/task/${taskId}`);
        const statusData = await statusResponse.json();

        // 根据后端的真实状态机流转
        if (statusData.state === 'SUCCESS') {
          setResult(statusData.result);
          setStatus("success");
          isTaskComplete = true;
        } else if (statusData.state === 'FAILURE') {
          throw new Error(statusData.error || "大模型节点发生物理熔断。");
        } else if (statusData.state === 'PROGRESS') {
          // 将后端 worker.py 里实时更新的状态，直接透传到前端 UI！
          setPollingStatusMsg(statusData.status);
        }

        // 没完成就物理休眠 2 秒，防止把后端 API 轰炸到宕机
        if (!isTaskComplete) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }

    } catch (error) {
      console.error(error);
      if (error instanceof Error) {
        setErrorMessage(`运算中断：${error.message}`);
      } else {
        setErrorMessage("运算中断：发生了未知的底层错误。");
      }
      setStatus("error");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-300 p-4 md:p-8 font-sans selection:bg-blue-500/30">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* 顶部标题栏 */}
        <header className="border-b border-slate-800 pb-6">
          <h1 className="text-3xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
            Amazon AI Agent 商业情报舱 (V5.0)
          </h1>
          <p className="text-slate-500 mt-2 text-sm">
            基于 Next.js Server Components 与高并发消息队列的双擎计算节点
          </p>
        </header>

        {/* 交互控制台：基于 CSS Grid 的 Bento 布局 */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* 左侧：双模式输入舱 */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl shadow-2xl space-y-6 relative overflow-hidden">
            {/* 装饰性光晕 */}
            <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 rounded-full bg-blue-500/5 blur-3xl pointer-events-none"></div>

            <div className="space-y-4 relative z-10">
              {/* 模式 A：URL 输入 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold px-2 py-1 rounded bg-blue-900/40 text-blue-400 border border-blue-800/50">
                    模式 A: 实时在线抓取
                  </span>
                </div>
                <input
                  type="text"
                  value={url}
                  onChange={handleUrlChange}
                  disabled={inputMode === "query" || status === "polling"}
                  placeholder="输入美国亚马逊商品链接..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                />
              </div>

              {/* 分隔符 */}
              <div className="flex items-center text-slate-600 text-xs font-bold my-2">
                <div className="flex-1 border-t border-slate-800"></div>
                <span className="px-3 uppercase tracking-widest">OR</span>
                <div className="flex-1 border-t border-slate-800"></div>
              </div>

              {/* 模式 B：Query 输入 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold px-2 py-1 rounded bg-emerald-900/40 text-emerald-400 border border-emerald-800/50">
                    模式 B: 本地 RAG 检索
                  </span>
                </div>
                <input
                  type="text"
                  value={userQuery}
                  onChange={handleQueryChange}
                  disabled={inputMode === "url" || status === "polling"}
                  placeholder="输入你想分析的具体问题 (如: 电池续航)"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          {/* 右侧：鉴权与执行舱 */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl shadow-2xl flex flex-col justify-between">
            <div className="space-y-4">
              <label className="block text-sm font-medium text-slate-400">
                系统访问权限核验
              </label>
              <input
                type="password"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                disabled={status === "polling"}
                placeholder="输入专属邀请码 (如: AI2026)"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all disabled:opacity-50"
              />
              {errorMessage && (
                <p className="text-red-400 text-xs mt-2 font-medium animate-pulse">{errorMessage}</p>
              )}
            </div>

            <button
              onClick={handleStartAnalysis}
              disabled={status === "polling"}
              className="mt-6 w-full bg-slate-100 hover:bg-white text-slate-900 disabled:bg-slate-800 disabled:text-slate-500 px-6 py-4 rounded-lg font-bold transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] disabled:shadow-none flex items-center justify-center gap-2"
            >
              {status === "polling" ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>算力引擎全载荷运转中...</span>
                </>
              ) : (
                "启动双脑协同分析"
              )}
            </button>
          </div>
        </section>

        {/* 状态与输出面板 (Bento Grid) */}
        <section className={`transition-all duration-700 ease-in-out ${status === 'idle' ? 'opacity-50 grayscale' : 'opacity-100 grayscale-0'}`}>

          {/* 空闲态 / 加载态 */}
          {(status === "idle" || status === "polling") && (
            <div className="bg-slate-900/50 border border-slate-800 border-dashed rounded-xl min-h-[300px] flex flex-col items-center justify-center text-slate-600">
              {status === "idle" ? (
                <p className="font-mono text-sm">[算力节点休眠中] 等待参数输入以唤醒 Actor-Critic 双脑模型...</p>
              ) : (
                <div className="space-y-4 text-center">
                  <div className="flex gap-2 justify-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-ping"></div>
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-ping" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-ping" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <p className="text-blue-400 font-mono text-sm animate-pulse">
                    {pollingStatusMsg || "[进程唤醒] 正在建立加密通道..."}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 成功态数据展示 */}
          {status === "success" && result && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in slide-in-from-bottom-8 fade-in duration-500">

              {/* 痛点卡片 */}
              <div className="bg-slate-900 border border-red-900/30 p-6 rounded-xl shadow-lg hover:border-red-500/50 transition-colors">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
                  <div className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]"></div>
                  <h3 className="text-lg font-bold text-slate-200">买家核心痛点</h3>
                </div>
                <ul className="space-y-3">
                  {result.pain_points.map((pt, idx) => (
                    <li key={idx} className="text-sm text-slate-400 leading-relaxed flex items-start gap-2">
                      <span className="text-red-500 font-mono text-xs mt-0.5 opacity-50">{(idx + 1).toString().padStart(2, '0')}</span>
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 卖点卡片 */}
              <div className="bg-slate-900 border border-emerald-900/30 p-6 rounded-xl shadow-lg hover:border-emerald-500/50 transition-colors">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
                  <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                  <h3 className="text-lg font-bold text-slate-200">核心卖点提炼</h3>
                </div>
                <ul className="space-y-3">
                  {result.selling_proposals.map((pt, idx) => (
                    <li key={idx} className="text-sm text-slate-400 leading-relaxed flex items-start gap-2">
                      <span className="text-emerald-500 font-mono text-xs mt-0.5 opacity-50">{(idx + 1).toString().padStart(2, '0')}</span>
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 模板卡片 (跨两列或单列展示，取决于屏幕大小) */}
              <div className="bg-slate-900 border border-purple-900/30 p-6 rounded-xl shadow-lg hover:border-purple-500/50 transition-colors">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
                  <div className="w-3 h-3 rounded-full bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]"></div>
                  <h3 className="text-lg font-bold text-slate-200">公关危机介入</h3>
                </div>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/50">
                  <p className="text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
                    {result.auto_reply_template}
                  </p>
                </div>
              </div>

            </div>
          )}

        </section>
      </div>
    </main>
  );
}