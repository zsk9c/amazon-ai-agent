from DrissionPage import ChromiumPage
import time

def scrape_amazon_reviews(url: str, target_count: int = 15) -> str:
    print("启动浏览器抓取数据...")
    page = ChromiumPage()
    page.get(url)
    
    print("页面已打开，如有弹窗请迅速手动关闭...")
    time.sleep(1.5) 
    
    # 采用优雅降级策略：不触发登录墙，仅在当前主页面深度滚动
    print("开始在主页面向下滚动，触发评论区懒加载...")
    for _ in range(2):
        page.scroll.down(4000)
        time.sleep(1.2)
        
    collected_reviews = set()
    
    print("正在提取主页面的评论元素...")
    review_elements = page.eles('@data-hook=review-body')
    if not review_elements:
        review_elements = page.eles('.review-text-content')
        
    for el in review_elements:
        content = el.text.strip()
        if content and len(content) > 10:
            collected_reviews.add(content)
            
    final_list = list(collected_reviews)[:target_count]
    
    if not final_list:
        return ""

    print(f"安全抓取完成，共获得 {len(final_list)} 条有效评论。")
    return "\n---\n".join(final_list)