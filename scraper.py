from DrissionPage import ChromiumOptions, ChromiumPage
import pandas as pd
import time

def scrape_amazon_reviews(url: str, target_count: int = 30) -> str:
    print("准备接管本地浏览器...")
    # 【核心反爬优化】：接管本地已登录的浏览器进程 (需要你提前打开一个调试端口)
    co = ChromiumOptions().set_local_port(9222)
    
    try:
        page = ChromiumPage(co)
    except Exception as e:
        print(f"接管失败，请确保你已经按照特殊指令启动了 Chrome。报错：{e}")
        return ""
        
    page.get(url)
    time.sleep(3) 
    
    # 尝试物理点击“查看更多评论”
    print("正在寻找‘查看更多评论’按钮...")
    more_btn = page.ele('@data-hook=see-all-reviews-link-foot', timeout=3)
    if more_btn:
        more_btn.click()
        time.sleep(3)
        print("成功进入深度评论区！因为携带了你的真实 Cookie，亚马逊放行了！")
        
        # 在专属评论页进行分页抓取
        for _ in range(3): # 抓 3 页
            page.scroll.down(2000)
            time.sleep(1.5)
            next_btn = page.ele('.a-last', timeout=2)
            if next_btn and 'a-disabled' not in next_btn.attr('class'):
                try:
                    next_btn.click()
                    time.sleep(2)
                except:
                    break
    else:
        print("未找到跳转按钮，在主页面强行收集...")
        for _ in range(2):
            page.scroll.down(4000)
            time.sleep(1.5)
        
    raw_reviews = []
    review_elements = page.eles('@data-hook=review-body')
    if not review_elements:
        review_elements = page.eles('.review-text-content')
        
    for el in review_elements:
        raw_reviews.append(el.text.strip())
            
    if not raw_reviews:
        return ""

    df = pd.DataFrame(raw_reviews, columns=['ReviewText'])
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)
    df = df[df['ReviewText'].str.len() > 20]
    
    clean_list = df['ReviewText'].head(target_count).tolist()
    print(f"Pandas 清洗完成！最终有效的高价值评论：{len(clean_list)} 条。")
    return "\n---\n".join(clean_list)