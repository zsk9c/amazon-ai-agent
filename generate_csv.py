import pandas as pd
import random

# 定义鼠标评论的五个核心商业维度与语料库 (包含 Pro/Con，保证 RAG 检索广度)
corpora = {
    # 维度一：电池与续航 (针对无线鼠标)
    "battery": [
        {"pro": "The battery life is abysmal, it dies in less than 2 hours. Do not buy this garbage for travel. The material feels extremely cheap and plastic-y.", "con": "Battery life is excellent, easily lasts two weeks with heavy use.", "keywords": ["battery", "dies", "charger", "travel"]},
        {"pro": "Extremely frustrated with the seller's return policy for the broken battery.", "con": "The companion app is terrible, it crashes constantly on my Android phone. Can't even update the firmware and check battery status.", "keywords": ["battery", "app", "crash", "warranty"]},
        {"pro": "Very comfortable for all-day wearing. My only issue is the Bluetooth connection occasionally drops when my phone is in my pocket.", "con": "The battery indicator is useful, works well with my Mac.", "keywords": ["battery", "bluetooth", "comfort"]},
    ],
    # 维度二：人体工学与手感 (针对所有鼠标)
    "ergonomics": [
        {"pro": "Looks premium, but smells funny, like some toxic chemical. The sound is okay, not worth $200 though.", "con": "Highly recommended, snaps smoothly, and very consistent tracking.", "keywords": ["smell", " premium", "comfort", "tracking"]},
        {"pro": "Way too small for my hands. Gave me severe wrist pain after just one day of gaming.", "con": "Ergonomics are top notch, perfect size and weight for productivity.", "keywords": ["small", "pain", "size", "weight", "hand"]},
        {"pro": "The texture is odd, feels slippery.", "con": "The side grips are fantastic, non-slip and comfortable.", "keywords": ["texture", "slippery", "grip", "comfortable"]},
    ],
    # 维度三：点击与追踪 (针对微动和传感器)
    "tracking": [
        {"pro": "The left click started double-clicking after 3 months. Worst durability.", "con": "Clicks are crystal clear and snappy. Highly recommended.", "keywords": ["double clicking", "durability", "snappy", "highly recommended"]},
        {"pro": "Sensor skipping is intolerable. The cursor jumps all over the screen.", "con": "Highly recommended, snaps smoothly, and very consistent tracking.", "keywords": ["skipping", "jumps", "consistent", "highly recommended", "tracking"]},
        {"pro": "The scroll wheel is broken. It scrolls down when I scroll up.", "con": "The scroll wheel has great tactile feedback.", "keywords": ["scroll wheel", "broken", "tactile"]},
    ],
    # 维度四：软件与驱动 (针对电竞/多功能鼠标)
    "software": [
        {"pro": "The companion app is terrible, it crashes constantly on my Android phone. Can't even update the firmware.", "con": "Highly recommended, snaps smoothly, and very consistent tracking.", "keywords": ["app", "crash", " highly recommended", "tracking"]},
        {"pro": "The software requires you to create an account and is always online. Big privacy concern.", "con": "Software is optional but excellent, easy to remap buttons.", "keywords": ["software", "account", "privacy", "excellent"]},
        {"pro": "RGB is buggy and won't sync with other devices.", "con": "RGB lighting is vibrant and easily customizable.", "keywords": ["rgb", "buggy", "sync", "lighting"]},
    ],
    # 维度五：价格与包装 (针对 MVP 的综合评论)
    "value": [
        {"pro": "Arrived broken. The left earbud has zero sound.", "con": "Price is okay, good value during the sale.", "keywords": ["broken", "zero sound", "price", "good value"]},
        {"pro": "Worst durability. Clicks are crystal clear and snappy.", "con": "A bit overpriced, but highly recommended.", "keywords": [" durability", "overpriced", " highly recommended"]},
        {"pro": "Texture is odd, feels slippery. The sided grips are fantastic.", "con": "Best value in the market right now.", "keywords": ["slippery", "fantastic", "best value", "market"]},
    ],
}

# 3. 极速造数核心逻辑
print("正在生成原始评论数据并启动物理去重引擎...")

reviews = []
# 循环生成数据
for _ in range(1000):
    category = random.choice(list(corpora.keys()))
    review_template = random.choice(corpora[category])
    
    content = f"Aspect: {category}. "
    content += f"{review_template['pro']} {review_template['con']} "
    content += f"Keywords: {', '.join(review_template['keywords'])}. "
    reviews.append(content)

# 4. Pandas 封箱与强行过滤
df = pd.DataFrame(reviews, columns=['ReviewText'])

original_count = len(df)
# 核心阻断：强制按文本内容去重，仅保留第一个出现的唯一语义
df = df.drop_duplicates(subset=['ReviewText'], keep='first')
final_count = len(df)

print(f"[数据清洗] 从 {original_count} 条生成数据中，成功切除了 {original_count - final_count} 条重复的垃圾克隆体。")

# 强制覆盖保存
df.to_csv('mock_data.csv', index=False)

print(f"造数成功！包含 {final_count} 条极度纯净语义的 'mock_data.csv' 已生成在你的项目根目录下。")