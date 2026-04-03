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
        
    if not news_data_str:
        print("沒有收到任何新聞資料")
        return

    # 1. 【核心修正】強大防呆解析：把 50 篇新聞全部救回來
    try:
        raw_data = json.loads(news_data_str)
        
        # 判斷 n8n 傳過來的各種變形格式
        if isinstance(raw_data, list):
            news_list = raw_data
        elif isinstance(raw_data, dict) and "data" in raw_data:
            news_list = raw_data["data"]
        else:
            news_list = [raw_data] if raw_data else []
            
        print("\n" + "="*50)
        print(f"🎉 成功接收到資料！總共抓取了 {len(news_list)} 則新聞。")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"解析 JSON 失敗: {e}")
        return

    if not news_list:
        print("沒有新聞資料可以處理")
        return

    # 2. 啟動中研院斷詞 (拿掉 level=3 以免報錯)
    titles = [news.get('title', '') for news in news_list]
    print("正在進行中研院斷詞，請稍候...")
    ws_driver = CkipWordSegmenter()
    ws_results = ws_driver(titles)

    # 3. 建立每則新聞的關鍵字特徵
    news_keywords = []
    for ws in ws_results:
        keywords = set([word for word in ws if len(word) > 1])
        news_keywords.append(keywords)

    # 4. 智慧分組 (Jaccard 相似度)
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

    # 5. 依照關聯數量排序，把熱點排在最前面
    groups.sort(key=lambda x: len(x), reverse=True)

    # 6. 分流處理：熱點事件 vs 獨立事件
    hot_groups = [g for g in groups if len(g) > 1]
    single_groups = [g for g in groups if len(g) == 1]

    # 7. 排版成純文字格式（安全，防 Telegram 格式錯誤）
    message = "📊 【中研院 NLP 智慧熱點戰報】\n\n"
    
    # 處理 2 則以上關聯的【熱點事件】
    if hot_groups:
        for g_idx, group in enumerate(hot_groups, 1):
            common_keywords = set.intersection(*(news_keywords[i] for i in group))
            topic = "、".join(list(common_keywords)[:3]) if common_keywords else "綜合議題"
            
            message += f"🔥 【熱點：{topic}】（共關聯 {len(group)} 則報導）\n"
            
            for n_idx in group:
                item = news_list[n_idx]
                title = item.get('title', '無標題').strip()
                desc = item.get('description', '').strip()
                link = item.get('link', '')
                
                # 防呆：如果真的沒摘要，就抓標題來用，絕不顯示空洞的「無摘要」
                if not desc:
                    desc = title
                    
                if len(desc) > 60:
                    desc = desc[:60] + "..."
                    
                message += f"📌 標題：{title}\n"
                message += f"📝 摘要：{desc}\n"
                if link:
                    message += f"🔗 連結：{link}\n"
                message += "-----------------------\n"
            message += "\n"
            
    # 處理 只有 1 則的【獨立事件】
    if single_groups:
        message += "━━━━━━━━━━━━━━━━━━━\n"
        message += "📰 其他（獨立事件） \n\n"
        for g in single_groups:
            n_idx = g[0]
            item = news_list[n_idx]
            title = item.get('title', '無標題').strip()
            desc = item.get('description', '').strip()
            link = item.get('link', '')
            
            if not desc:
                desc = title
                
            if len(desc) > 60:
                desc = desc[:60] + "..."
                
            message += f"📌 標題：{title}\n"
            message += f"📝 摘要：{desc}\n"
            if link:
                message += f"🔗 連結：{link}\n"
            message += "-----------------------\n"

    # 8. 【日誌監視器】在 GitHub 日誌上直接印出戰報內容
    print("\n" + "="*50)
    print("📢 【即將發送給 Telegram 的內容預覽】如下：")
    print("="*50)
    print(message)
    print("="*50 + "\n")

    # 9. 發送 Telegram (拿掉容易出錯的 Markdown 模式)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message
    }
    
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        print("Telegram 戰報發送成功！")
    else:
        print(f"發送失敗，錯誤碼: {res.status_code}")
        print(f"錯誤訊息: {res.text}")

if __name__ == "__main__":
    main()
