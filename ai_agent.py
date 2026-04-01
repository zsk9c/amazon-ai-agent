import requests
import json
import os
from dotenv import load_dotenv
# 引入工业级重试框架
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

# ==========================================
# 工业级防御基建：定义系统级异常类
# ==========================================
class HallucinationError(Exception):
    """当裁判大脑核对出捏造数据时抛出此异常"""
    pass

class JSONSyntaxError(Exception):
    """当模型输出无法被解析的非法 JSON 时抛出此异常"""
    pass

# ==========================================
# 左半脑：处理 V2.0 在线实时爬虫的原始数据
# ==========================================
def analyze_reviews_with_ai(reviews_text: str) -> dict:
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv("GROQ_API_KEY") 
    reviews_text = str(reviews_text)[:4000]
    
    if not api_key:
        raise ValueError("严重错误：未找到 GROQ_API_KEY。")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": """你是一个资深的跨境电商产品总监。请阅读以下买家评论，并输出规范的 JSON 格式深度分析报告。
                严格遵守以下格式和语言绝对约束：
                1. 'pain_points': 基于差评提炼的产品物理缺陷，为下一代产品提供 3 条改进建议。（必须为字符串数组，使用【简体中文】）
                2. 'selling_proposals': 基于买家强烈赞好的点，为 Listing 上架提炼 3 条核心卖点。（必须为字符串数组，使用【简体中文】）
                3. 'auto_reply_template': 针对最严重的 1 个客诉问题，撰写 1 条用于安抚客户的专业客服邮件模板。（必须为字符串，使用【纯英文】输出！）"""
            },
            {
                "role": "user",
                "content": f"买家原始评论：\n{reviews_text}"
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 1500  # 将 8192 改为 1500，把空间让给输入文本
    }
    
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return json.loads(response.json()['choices'][0]['message']['content'])


# ==========================================
# 右半脑 (企业重构版)：Actor-Critic 架构与 Tenacity 熔断
# ==========================================
def analyze_reviews_with_ai_with_rag(context_text: str, user_query: str = None) -> dict:
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv("GROQ_API_KEY") 
    
    if not api_key:
        raise ValueError("严重错误：未找到 GROQ_API_KEY。")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    pruned_context = context_text[:8000] 
    
    # 状态持久化：使用列表在多次重试之间传递被裁判打回的原因
    feedback_history = [] 

    # 核心重构：使用装饰器将重试逻辑与业务逻辑彻底解耦
    @retry(
        stop=stop_after_attempt(3), 
        # 指数退避算法：初次失败休眠 4 秒，再次失败休眠 8 秒，以此类推，完美避开 API 限流墙
        wait=wait_exponential(multiplier=2, min=4, max=10), 
        retry=(retry_if_exception_type(HallucinationError) | retry_if_exception_type(JSONSyntaxError)),
        reraise=True 
    )
    def _actor_critic_loop():
        print("\n[算力调度] -> 启动 Agent A (Writer) 线程...")
        
        writer_system_prompt = """你是一个资深的跨境电商产品总监。
请根据以下检索到的【精准评论上下文】，输出规范的 JSON 分析报告。绝不能捏造！

【极度严苛的去重与长度控制指令】：
1. 绝对语义去重：你提取的 pain_points 和 selling_proposals 内部，绝对禁止出现重复或语义高度相似的条款。如果多条评论都在抱怨“电池寿命短”，你只能总结为一条“电池寿命极短，仅能维持2小时”。
2. 宁缺毋滥，拒绝凑数：如果原文归纳去重后只有 1 个痛点，数组长度就必须严格为 1。绝对禁止为了凑数而复制已有观点或进行无意义的同义词替换扩写！
3. 保留两极分化：买家评论中经常存在两极分化（如有人赞电池，有人骂电池）。这属于真实客诉情况，请分别在痛点和卖点中如实记录，这不属于重复。

严格遵守以下 JSON 格式：
1. 'pain_points': 基于缺陷提炼建议。（字符串数组，【简体中文】，必须严格去重。无则写 ["无"]）
2. 'selling_proposals': 基于赞点提炼卖点。（字符串数组，【简体中文】，必须严格去重。无则写 ["无"]）
3. 'auto_reply_template': 撰写专业客服邮件模板。（字符串，【纯英文】）"""

        writer_content = f"【精确上下文】：\n{pruned_context}\n"
        if user_query:
            writer_content = f"【用户问题】：{user_query}\n" + writer_content
            
        if feedback_history:
            # 提取最后一次被骂的记录
            writer_content += f"\n【法官退回警告】：{feedback_history[-1]}\n请务必修正！注意：JSON中绝对不能有真实物理换行，必须用 \\n 转义！"

        writer_payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": writer_system_prompt},
                {"role": "user", "content": writer_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        
        writer_resp = requests.post(api_url, headers=headers, json=writer_payload).json()
        if 'error' in writer_resp:
            raise ValueError(f"API 致命阻断: {writer_resp['error']}")
            
        draft_report_str = writer_resp['choices'][0]['message']['content']

        # 第一道防线：语法守卫
        try:
            draft_json = json.loads(draft_report_str)
        except json.JSONDecodeError as e:
            print("[语法守卫] -> 拦截非法 JSON 输出，抛出系统级异常。")
            feedback_history.append(f"JSON 格式严重错误！解析器报错：{str(e)}。请检查转义符！")
            raise JSONSyntaxError("Writer 语法崩溃")

        print("[算力调度] -> 启动 Agent B (Critic) 线程进行数据核验...")
        
        critic_system_prompt = """你是一个极其严苛的数据审查员 (Critic)。
        你的任务是核对报告：
        1. 幻觉核验：是否捏造了上下文中没有的信息？
        2. 冗余核验：是否存在语义重复或观点复读？
        【重要】：只要原始上下文中有一位买家提及，就不算幻觉。但若同一观点出现两次，必须判定为冗余。
        输出 JSON：
        {"is_hallucinating": true或false, "is_redundant": true或false, "feedback": "描述具体问题或输出'无'"}"""

        critic_content = f"【原始上下文】：\n{pruned_context}\n\n【待审核报告】：\n{draft_report_str}"
        critic_payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": critic_system_prompt},
                {"role": "user", "content": critic_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0 
        }

        critic_resp = requests.post(api_url, headers=headers, json=critic_payload).json()
        if 'error' in critic_resp:
             raise ValueError(f"裁判 API 致命阻断: {critic_resp['error']}")
             
        critic_raw_str = critic_resp['choices'][0]['message']['content']

        # 裁判防弹衣
        try:
            critic_result = json.loads(critic_raw_str)
        except json.JSONDecodeError:
            print("[系统保护] -> 裁判模块抛出语法异常。")
            feedback_history.append("内部系统警告：裁判模块发生了语法错误。请重新生成底稿。")
            raise JSONSyntaxError("Critic 语法崩溃")

        # 核心对抗逻辑：如果发现幻觉，直接通过 Raise 抛出异常炸毁当前执行流
        if not critic_result.get("is_hallucinating", True):
            print("[架构验收] -> 裁判审核通过，输出高保真数据。")
            return draft_json 
        else:
            feedback_msg = critic_result.get("feedback")
            print(f"[数据熔断] -> 发现捏造数据：{feedback_msg}。抛出异常触发重试池...")
            feedback_history.append(feedback_msg)
            raise HallucinationError("数据一致性核验失败")

    # 外层包装：捕获所有重试失败后的最终异常，实现绝对的优雅降级
    try:
        return _actor_critic_loop()
    except Exception as e:
        print(f"\n[系统降级] -> 节点算力耗尽或遭致命错误 ({str(e)})，执行容灾输出。")
        return {
            "pain_points": ["当前请求排队中，请稍后再试 (Token Limit/Retry Exhausted)"], 
            "selling_proposals": ["系统执行了熔断降级操作"], 
            "auto_reply_template": "System Fallback: Analysis interrupted due to strict data validation policy."
        }