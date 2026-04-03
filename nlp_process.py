import os
import json
import requests
from ckip_transformers.nlp import CkipWordSegmenter

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    news_data_str = os.environ.get("NEWS_DATA")
    
    if not token or not chat_id:
        print("缺少 Telegram 設定")
        return
        
    try:
        news_list = json.loads(news_data_str)
    except Exception as e:
        print(f"解析 JSON 失敗: {e}")
        return

    if not news_list:
        print("沒有新聞資料")
        return

    # 1. 啟動中研院斷詞 (對標題進行斷詞)
    titles = [news.get('title', '') for news in news_list]
    print("正在進行中研院斷詞...")
    ws_driver = CkipWordSegmenter(level=3)
    ws_results = ws_driver(titles)

    # 2. 建立每則新聞的關鍵字特徵
    news_keywords = []
    for ws in ws_results:
        keywords = set([word for word in ws if len(word) > 1])
        news_keywords.append(keywords)

    # 3. 智慧分組 (Jaccard 相似度)
    groups = []
    for i, keywords in enumerate(news_keywords):
        placed = False
        for group in groups:
            sample_idx = group[0]
            intersection = keywords.intersection(news_keywords[sample_idx])
            union = keywords.union(news_keywords[sample_idx])
            similarity = len(intersection) / len(union) if len(union) > 0 else 0
            
            if similarity > 0.25: # 相似度門檻
                group.append(i)
                placed = True
                break
        if not placed:
            groups.append([i])

    # 4. 依照關聯數量排序，把熱點排在最前面
    groups.sort(key=lambda x: len(x), reverse=True)

    # 5. 分流處理：熱點事件 vs 獨立事件
    hot_groups = [g for g in groups if len(g) > 1]
    single_groups = [g for g in groups if len(g) == 1]

    # 6. 排版成你指定的格式
    message = "📊 【戰報】\n\n"
    
    # 處理 2 則以上關聯的【熱點事件】
    if hot_groups:
        for g_idx, group in enumerate(hot_groups, 1):
            common_keywords = set.intersection(*(news_keywords[i] for i in group))
            topic = "、".join(list(common_keywords)[:3]) if common_keywords else "綜合議題"
            
            message += f"🔥 【熱點：{topic}】（共關聯 {len(group)} 則報導）\n"
            
            for n_idx in group:
                item = news_list[n_idx]
                title = item.get('title', '無標題').strip()
                desc = item.get('description', '無摘要').strip()
                link = item.get('link', '')
                
                if len(desc) > 60:
                    desc = desc[:60] + "..."
                    
                message += f"📌 **標題**：{title}\n"
                message += f"📝 **摘要**：{desc}\n"
                if link:
                    message += f"🔗 **連結**：{link}\n"
                message += "-----------------------\n"
            message += "\n"
            
    # 處理 只有 1 則的【獨立事件】
    if single_groups:
        message += "━━━━━━━━━━━━━━━━━━━\n"
        message += "📰 其他 \n\n"
        for g in single_groups:
            n_idx = g[0]
            item = news_list[n_idx]
            title = item.get('title', '無標題').strip()
            desc = item.get('description', '無摘要').strip()
            link = item.get('link', '')
            
            if len(desc) > 60:
                desc = desc[:60] + "..."
                
            message += f"📌 **標題**：{title}\n"
            message += f"📝 **摘要**：{desc}\n"
            if link:
                message += f"🔗 **連結**：{link}\n"
            message += "-----------------------\n"

    # 7. 發送 Telegram
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message,
        "parse_mode": "Markdown"
    }
    
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        # 如果因為特殊字元導致 Markdown 失敗，降級用純文字發送
        payload.pop("parse_mode")
        requests.post(url, json=payload)
        print("以純文字模式發送成功！")
    else:
        print("Telegram 戰報發送成功！")

if __name__ == "__main__":
    main()
