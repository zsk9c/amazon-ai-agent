import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 左半脑：处理 V2.0 在线实时爬虫的原始数据
# ==========================================
def analyze_reviews_with_ai(reviews_text: str) -> dict:
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv("GROQ_API_KEY") 
    
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
                "content": """你是一个资深的跨境电商产品总监。
    请根据以下检索到的【精准评论上下文】，输出规范的 JSON 分析报告。绝不能捏造上下文中不存在的信息！
    严格遵守格式：
    1. 'pain_points': 基于缺陷提炼建议。（字符串数组，【简体中文】。数量根据上下文实际情况决定，如无提及请写 ["无"]）
    2. 'selling_proposals': 基于赞点提炼卖点。（字符串数组，【简体中文】。数量根据上下文实际情况决定，如无提及请写 ["无"]）
    3. 'auto_reply_template': 撰写专业客服邮件模板。（字符串，【纯英文】）"""
            },
            {
                "role": "user",
                "content": f"买家原始评论：\n{reviews_text}"
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 4096 
    }
    
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return json.loads(response.json()['choices'][0]['message']['content'])


# ==========================================
# 右半脑 (V4.0 升级版)：多脑协同 (Actor-Critic) 与幻觉控制
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
    
    writer_system_prompt = """你是一个资深的跨境电商产品总监。
    请根据以下检索到的【精准评论上下文】，输出规范的 JSON 分析报告。绝不能捏造上下文中不存在的信息！
    严格遵守格式：
    1. 'pain_points': 基于缺陷提炼建议。（字符串数组，【简体中文】。数量根据上下文实际情况决定，如无提及请写 ["无"]）
    2. 'selling_proposals': 基于赞点提炼卖点。（字符串数组，【简体中文】。数量根据上下文实际情况决定，如无提及请写 ["无"]）
    3. 'auto_reply_template': 撰写专业客服邮件模板。（字符串，【纯英文】）"""

    critic_system_prompt = """你是一个极其严苛的数据审查员 (Critic)。
    你的唯一任务是核对 Writer 生成的报告是否出现了【幻觉】（即：报告中提到了原始上下文中根本没有提到的缺陷或卖点）。
    请输出 JSON：
    {"is_hallucinating": true或false, "feedback": "如果造假，严厉指出哪里捏造了；如果没有捏造，输出'无'。"}"""

    feedback_history = ""
    max_retries = 1

    # 多脑协同控制流：While 重试机制
    for attempt in range(max_retries):
        print(f"\n[多脑协同] -> Agent A (Writer) 正在进行第 {attempt + 1} 次起草...")
        
        # 1. 组装 Writer 的输入
        writer_content = f"【精确上下文】：\n{context_text}\n"
        if user_query:
            writer_content = f"【用户问题】：{user_query}\n" + writer_content
        if feedback_history:
            writer_content += f"\n【系统退回警告】：{feedback_history}\n请务必修正上述错误！注意：JSON 字符串中绝对不能有真实物理换行，必须用 \\n 转义！"

        writer_payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": writer_system_prompt},
                {"role": "user", "content": writer_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        
        # 触发 Writer 思考
        writer_resp = requests.post(api_url, headers=headers, json=writer_payload).json()
        draft_report_str = writer_resp['choices'][0]['message']['content']

        # ==========================================
        # 第一层防御：语法守卫 (Syntax Guard)
        # ==========================================
        try:
            draft_json = json.loads(draft_report_str)
            print("[多脑协同] -> 语法守卫通过：JSON 格式完全合法。")
        except json.JSONDecodeError as e:
            print(f"[多脑协同] -> 警告！语法守卫拦截！Writer 输出了非法 JSON。打回重写！")
            feedback_history = f"你生成的 JSON 格式严重错误！解析器报错：{str(e)}。请确保邮件模板中的换行全部转义为 '\\n'，严禁直接使用物理换行！"
            continue 

        # ==========================================
        # 第二层防御：语义裁判 (Semantic Critic)
        # ==========================================
        print(f"[多脑协同] -> Agent B (Critic) 正在核查底稿数据一致性...")
        
        critic_content = f"【原始上下文】：\n{context_text}\n\n【待审核报告】：\n{draft_report_str}"
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
        critic_raw_str = critic_resp['choices'][0]['message']['content']

        # 核心终极防御：裁判自身防弹衣
        try:
            critic_result = json.loads(critic_raw_str)
        except json.JSONDecodeError as e:
            print(f"[多脑协同] -> 警告！裁判自身输出非法 JSON 导致脑震荡。强行进入下一轮循环！")
            feedback_history = "内部系统警告：裁判模块刚才发生了语法解析错误。请你（Writer）重新生成一份更精简、绝对规范的底稿供重新审查。"
            continue

        # 3. 核心熔断逻辑
        if not critic_result.get("is_hallucinating", True):
            print("[多脑协同] -> 裁判审核通过！未发现幻觉，交付最终报告。")
            return draft_json 
        else:
            print(f"[多脑协同] -> 警告！裁判发现幻觉，打回重写！原因：{critic_result.get('feedback')}")
            feedback_history = critic_result.get("feedback")

    # ==========================================
    # 终极兜底 (Fallback)
    # ==========================================
    print("\n[多脑协同] -> 达到最大重试次数，系统强制交付当前可用版本。")
    try:
        return json.loads(draft_report_str)
    except:
        return {"pain_points": ["系统解析严重错误"], "selling_proposals": ["系统解析严重错误"], "auto_reply_template": "System Error: Output corrupted."}