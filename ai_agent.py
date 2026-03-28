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
                "content": """你是一个资深的跨境电商产品总监。请阅读以下买家评论，并输出规范的 JSON 格式深度分析报告。
                必须包含以下三个键 (全部为字符串数组，且必须使用简体中文)：
                1. 'pain_points': 基于差评提炼的产品物理缺陷，为下一代产品的【选品和工厂开模】提供 3 条改进建议。
                2. 'selling_proposals': 基于买家强烈赞好的点，为【亚马逊 Listing 上架】提炼 3 条英文 Bullet Points (卖点)。
                3. 'auto_reply_template': 针对最严重的 1 个客诉问题，撰写 1 条用于安抚客户的专业英文客服邮件模板。"""
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
# 右半脑：处理 V3.0 RAG 本地记忆库的检索数据
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
    
    system_prompt = """你是一个资深的跨境电商产品总监。
    请根据以下从本地历史记忆库中检索到的【精准评论上下文】，输出规范的 JSON 分析报告。

    如果你是针对特定的用户问题回答，请确保分析深度契合问题场景。绝不能捏造上下文中不存在的信息。

    必须包含以下三个键 (字符串数组或字符串，使用简体中文)：
    1. 'pain_points': 基于检索到的缺陷，为下一代产品提供改进建议。
    2. 'selling_proposals': 基于检索到的赞点，提炼英文 Bullet Points。
    3. 'auto_reply_template': 针对当前上下文中最严重的一个客诉，撰写专业英文客服邮件模板。"""

    user_content = f"【检索到的精准评论上下文】：\n{context_text}"
    if user_query:
        user_content = f"【用户想具体分析的问题】：{user_query}\n\n" + user_content
        
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 4096 
    }
    
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return json.loads(response.json()['choices'][0]['message']['content'])