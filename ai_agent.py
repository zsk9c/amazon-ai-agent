import requests
import json
import os
from dotenv import load_dotenv
# 引入工业级重试框架
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
from schemas import AIAnalysisResult

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
# 左半脑：处理 V2.0 在线实时爬虫的原始数据 (V6.0 装甲升级版)
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
    
    feedback_history = []

    # 引入 Tenacity 重试防线：如果大模型输出非法结构，自动打回重写
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=2, min=4, max=10), 
        retry=(retry_if_exception_type(JSONSyntaxError)),
        reraise=True 
    )
    def _single_agent_loop():
        print("\n[算力调度] -> 启动 Agent (Writer) 处理在线抓取数据...")
        
        system_prompt = """你是一个资深的跨境电商产品总监。
请根据以下检索到的【精准评论上下文】，输出规范的 JSON 分析报告。绝不能捏造！

【极度严苛的去重与长度控制指令】：
1. 绝对语义去重：提取的 pain_points 和 selling_proposals 内部，绝对禁止出现重复或语义高度相似的条款！
2. 宁缺毋滥，拒绝凑数：如果原文归纳去重后只有 1 个痛点，数组长度就必须严格为 1。绝对禁止为了凑数而扩写！如果毫无相关内容，必须输出 ["无相关反馈"]。
3. 保留两极分化：买家评论中经常存在两极分化，这属于真实客诉情况，请分别在痛点和卖点中如实记录，不属于重复。

严格遵守以下 JSON 格式：
1. 'pain_points': 基于缺陷提炼建议。（字符串数组，【简体中文】，必须严格去重。）
2. 'selling_proposals': 基于赞点提炼卖点。（字符串数组，【简体中文】，必须严格去重。）
3. 'auto_reply_template': 撰写专业客服邮件模板。（【极其重要】：必须是普通的纯文本字符串！绝对禁止使用字典嵌套！使用纯英文）"""

        user_content = f"买家原始评论：\n{reviews_text}"
        if feedback_history:
            user_content += f"\n【系统警告】：{feedback_history[-1]}\n请务必修复 JSON 结构错误，特别是 auto_reply_template 必须是纯字符串！"

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 1500 
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        if 'error' in response.json():
            raise ValueError(f"API 致命阻断: {response.json()['error']}")
            
        raw_content = response.json()['choices'][0]['message']['content']
        
        try:
            # Pydantic 刚性校验
            validated_data = AIAnalysisResult.model_validate_json(raw_content)
            print("[架构验收] -> 在线数据 JSON 结构校验完美，输出高保真数据。")
            return validated_data.model_dump()
        except ValidationError as e:
            print("[结构守卫] -> 拦截到结构非法的 JSON 输出 (如字典嵌套)，物理阻断。")
            error_details = e.json()
            feedback_history.append(f"JSON 结构验证失败。报错信息：{error_details}。")
            raise JSONSyntaxError("Writer 结构崩溃")

    try:
        return _single_agent_loop()
    except Exception as e:
        print(f"\n[系统降级] -> 在线分析节点遭致命错误 ({str(e)})，执行容灾输出。")
        return {
            "pain_points": ["分析过程中数据结构持续异常，已熔断。"], 
            "selling_proposals": ["系统降级保护"], 
            "auto_reply_template": "System Fallback: Failed to generate valid string template."
        }


# ==========================================
# 右半脑 (企业重构版)：单体高能架构 (彻底切除内耗裁判)
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
    
    # ==========================================
    # 物理观测探针
    # ==========================================
    print("\n" + "="*50)
    print("【RAG 向量检索底稿透视】")
    print(f"总字符长度: {len(pruned_context)}")
    print("内容预览:")
    print(pruned_context)
    print("="*50 + "\n")
    
    feedback_history = [] 

    # 【手术刀 1】：从重试机制中彻底移除 HallucinationError，只保留结构异常校验
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=2, min=4, max=10), 
        retry=retry_if_exception_type(JSONSyntaxError),
        reraise=True 
    )
    def _single_agent_loop():
        print("\n[算力调度] -> 启动 Agent (Writer) 进行 RAG 数据提炼...")
        
        writer_system_prompt = """你是一个资深的跨境电商产品总监。
请根据以下检索到的【精准评论上下文】，输出规范的 JSON 分析报告。绝不能捏造！

【极度严苛的去重与长度控制指令】：
1. 绝对语义去重：提取的 pain_points 和 selling_proposals 内部，绝对禁止出现重复或语义高度相似的条款！
2. 宁缺毋滥，拒绝凑数：如果原文归纳去重后只有 1 个痛点，数组长度就必须严格为 1。绝对禁止为了凑数而扩写！如果毫无相关内容，必须输出 ["无相关反馈"]。
3. 保留两极分化：买家评论中经常存在两极分化，这属于真实客诉情况，请分别在痛点和卖点中如实记录，不属于重复。

严格遵守以下 JSON 格式：
1. 'pain_points': 基于缺陷提炼建议。（字符串数组，【简体中文】，必须严格去重。）
2. 'selling_proposals': 基于赞点提炼卖点。（字符串数组，【简体中文】，必须严格去重。）
3. 'auto_reply_template': 撰写专业客服邮件模板。（【极其重要】：必须是普通的纯文本字符串！绝对禁止使用字典嵌套！使用纯英文）"""

        writer_content = f"【精确上下文】：\n{pruned_context}\n"
        if user_query:
            writer_content = f"【用户问题】：{user_query}\n" + writer_content
            
        if feedback_history:
            writer_content += f"\n【系统警告】：{feedback_history[-1]}\n请务必修复 JSON 结构错误，特别是 auto_reply_template 必须是纯字符串！"

        writer_payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": writer_system_prompt},
                {"role": "user", "content": writer_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1 # 【物理降温】：调低温度至 0.1，让模型输出更保守，物理抑制幻觉
        }
        
        writer_resp = requests.post(api_url, headers=headers, json=writer_payload).json()
        if 'error' in writer_resp:
            raise ValueError(f"API 致命阻断: {writer_resp['error']}")
            
        draft_report_str = writer_resp['choices'][0]['message']['content']

        # ==========================================
        # 【手术刀 2】：只要通过 Pydantic 刚性结构测试，立刻放行，彻底废除裁判核对
        # ==========================================
        try:
            draft_pydantic_obj = AIAnalysisResult.model_validate_json(draft_report_str)
            draft_json = draft_pydantic_obj.model_dump() 
            print("[架构验收] -> RAG 数据 JSON 结构校验完美，输出高保真数据。")
            return draft_json # 直接返回，阻断后面的冗余网络请求
            
        except ValidationError as e:
            print("[结构守卫] -> 拦截到结构非法的 JSON 输出，物理阻断。")
            error_details = e.json()
            feedback_history.append(f"JSON 结构验证失败。报错信息：{error_details}。")
            raise JSONSyntaxError("Writer 结构崩溃")

    # 外层包装：捕获所有重试失败后的最终异常，实现绝对的优雅降级
    try:
        return _single_agent_loop()
    except Exception as e:
        print(f"\n[系统降级] -> 节点算力耗尽或遭致命错误 ({str(e)})，执行容灾输出。")
        return {
            "pain_points": ["当前请求排队中，请稍后再试 (Token Limit/Retry Exhausted)"], 
            "selling_proposals": ["系统执行了熔断降级操作"], 
            "auto_reply_template": "System Fallback: Analysis interrupted due to strict data validation policy."
        }