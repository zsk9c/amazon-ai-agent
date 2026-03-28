import time
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
    
    # 核心优化 1：极限物理截断，将上下文压榨至 800 字符，防止 TPM 击穿
    pruned_context = context_text[:800]
    
    writer_system_prompt = """你是一个资深的跨境电商产品总监。
    请根据以下检索到的【精准评论上下文】，输出规范的 JSON 分析报告。绝不能捏造上下文中不存在的信息！
    严格遵守格式：
    1. 'pain_points': 基于缺陷提炼建议。（字符串数组，【简体中文】。数量根据实际情况，无则写 ["无"]）
    2. 'selling_proposals': 基于赞点提炼卖点。（字符串数组，【简体中文】。数量根据实际情况，无则写 ["无"]）
    3. 'auto_reply_template': 撰写专业客服邮件模板。（字符串，【纯英文】）"""

    critic_system_prompt = """你是一个极其严苛的数据审查员 (Critic)。
    你的唯一任务是核对 Writer 生成的报告是否出现了【幻觉】。
    请输出 JSON：
    {"is_hallucinating": true或false, "feedback": "如果造假，严厉指出哪里捏造了；如果没有捏造，输出'无'。"}"""

    feedback_history = ""
    # 核心优化 2：降低最大重试次数为 1，最多只允许一次返工
    max_retries = 2 

    for attempt in range(max_retries):
        # 核心优化 3：ATP 恢复机制 (如果是重试，强制休眠 6 秒，避开每分钟并发限制)
        if attempt > 0:
            print(f"[系统保护] -> 触发 Token 速率限制保护，强制休眠 6 秒...")
            time.sleep(6)

        print(f"\n[多脑协同] -> Agent A (Writer) 正在进行第 {attempt + 1} 次起草...")
        
        # 注意这里使用的是 pruned_context
        writer_content = f"【精确上下文】：\n{pruned_context}\n"
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
        
        writer_resp = requests.post(api_url, headers=headers, json=writer_payload).json()
        
        # 兜底：如果 Groq 直接在这一步就抛出了 Token 限制的错
        if 'error' in writer_resp:
             print(f"[致命错误] API 报错: {writer_resp['error']}")
             return {"pain_points": ["API Token 耗尽"], "selling_proposals": ["请稍后再试"], "auto_reply_template": "Rate limit exceeded."}
             
        draft_report_str = writer_resp['choices'][0]['message']['content']

        try:
            draft_json = json.loads(draft_report_str)
        except json.JSONDecodeError as e:
            print(f"[多脑协同] -> 警告！语法守卫拦截！Writer 输出了非法 JSON。打回重写！")
            feedback_history = f"生成的 JSON 格式严重错误！请确保转义换行符为 '\\n'！"
            continue 

        # ==========================================
        # 新增限流对抗：给 Groq 的计费漏桶 3 秒钟的回血时间
        # ==========================================
        print("[系统保护] -> 正在为裁判大脑分配算力配额，短暂休眠 3 秒...")
        time.sleep(3)

        print(f"[多脑协同] -> Agent B (Critic) 正在核查底稿数据一致性...")
        
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
             print(f"[致命错误] API 报错: {critic_resp['error']}")
             return draft_json # 如果裁判被限流，直接强行返回一审底稿
             
        critic_raw_str = critic_resp['choices'][0]['message']['content']

        try:
            critic_result = json.loads(critic_raw_str)
        except json.JSONDecodeError as e:
            print(f"[多脑协同] -> 警告！裁判自身脑震荡。强行进入下一轮循环！")
            feedback_history = "内部系统警告：裁判模块发生了语法错误。请重新生成底稿。"
            continue

        if not critic_result.get("is_hallucinating", True):
            print("[多脑协同] -> 裁判审核通过！未发现幻觉，交付最终报告。")
            return draft_json 
        else:
            print(f"[多脑协同] -> 警告！裁判发现幻觉，打回重写！原因：{critic_result.get('feedback')}")
            feedback_history = critic_result.get("feedback")

    print("\n[多脑协同] -> 达到最大重试次数，系统强制交付当前可用版本。")
    try:
        return json.loads(draft_report_str)
    except:
        return {"pain_points": ["系统解析严重错误"], "selling_proposals": ["系统解析严重错误"], "auto_reply_template": "System Error: Output corrupted."}