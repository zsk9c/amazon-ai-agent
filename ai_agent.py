import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

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