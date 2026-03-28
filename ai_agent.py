import requests
import json
import os
from dotenv import load_dotenv

# 核心安全逻辑：从隐藏的 .env 文件加载环境变量
load_dotenv()

def analyze_reviews_with_ai(reviews_text: str) -> dict:
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    
    # 核心安全逻辑：通过系统级变量读取，代码中不再包含任何明文密码
    api_key = os.getenv("GROQ_API_KEY") 
    
    if not api_key:
        raise ValueError("严重错误：未找到 GROQ_API_KEY。请检查 .env 文件是否配置正确。")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                # 【核心修复】：增加条数限制，防止输出无限膨胀导致 Token 溢出
                "content": "你是一个严谨的跨境电商数据分析专家。请阅读以下买家评论，提取该产品的核心优点和缺点。无论原始评论是什么语言，你必须使用规范的简体中文输出结果，并且严格输出为 JSON 格式。包含 'pros' (优点列表) 和 'cons' (缺点列表) 两个键。注意：请将优缺点高度概括，每项最多保留 5 到 8 条最核心的结论，绝不能生成冗长的列表。"
            },
            {
                "role": "user",
                "content": f"以下是真实的买家评论：\n{reviews_text}"
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 4096 # 【核心修复】：将输出上限扩充 4 倍，保证 JSON 绝对能完美闭合
    }
    
    print("正在向大模型发送网络请求...")
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        print(f"大模型 API 拒绝请求，真实报错详情：{response.text}")
        
    response.raise_for_status()
    result_json_str = response.json()['choices'][0]['message']['content']
    
    return json.loads(result_json_str)