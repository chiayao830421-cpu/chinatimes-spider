import os
import sys
import json
import requests
from sentence_transformers import SentenceTransformer, util

def main():
    # 1. 從系統參數（sys.argv）直接讀取，避開 YAML 讀取問題
    if len(sys.argv) < 4:
        print("錯誤：傳入的參數不足。")
        return
        
    token = sys.argv[1]
    chat_id = sys.argv[2]
    news_data_str = sys.argv[3]
    
    if not token or token == "${{ secrets.TELEGRAM_TOKEN }}":
        print("缺少 Telegram Token 或 GitHub Secrets 讀取失敗")
        return
        
    if not chat_id:
        print("缺少 Telegram Chat ID")
        return
        
    if not news_data_str:
        print("沒有收到任何新聞資料")
        return

    # 2. 解析 n8n 丟過來的新聞陣列
    news_list = []
    try:
        raw_data = json.loads(news_data_str)
        
        if isinstance(raw_data, list):
            news_list = raw_data
        elif isinstance(raw_data, dict):
            if "allNews" in raw_data:
                news_list = raw_data["allNews"]
            else:
                for val in raw_data.values():
                    if isinstance(val, list):
                        news_list = val
                        break
                if not news_list:
                    news_list = [raw_data]
                    
        print(f"\n🎉 成功接收到資料！總共抓取了 {len(news_list)} 則新聞。")
        
    except Exception as e:
        print(f"解析 JSON 失敗: {e}")
        return

    if len(news_list) == 0:
        print("沒有新聞資料可以處理")
        return

    # 3. 載入免費的中文向量模型
    print("正在載入中文向量模型，請稍候...")
    model = SentenceTransformer('shibing624/text2vec-base-chinese')

    # 4. 把新聞的標題 + 摘要結合成一段話算向量
    sentences = []
    for item in news_list:
        title = item.get('title', '').strip()
        summary = item.get('summary', '').strip()
        # 如果沒摘要就用標題
        text = f"{title} {summary if summary else title}"
        sentences.append(text)

    print("正在進行語意向量計算...")
    embeddings = model.encode(sentences, convert_to_tensor=True)

    # 5. 使用向量相似度進行分組
    groups = []
    processed = [False] * len(news_list)

    for i in range(len(news_list)):
        if processed[i]:
            continue
            
        current_group = [i]
        processed[i] = True
        
        for j in range(i + 1, len(news_list)):
            if processed[j]:
                continue
                
            # 計算兩篇新聞的語意相似度
            similarity = util.cos_sim(embeddings[i], embeddings[j]).item()
            
            # 閾值設定 0.65，大於這個值代表高機率在講同一件事
            if similarity > 0.65:
                current_group.append(j)
                processed[j] = True
                
        groups.append(current_group)

    # 6. 排序與產出 Telegram 訊息
    groups.sort(key=lambda x: len(x), reverse=True)
    hot_groups = [g for g in groups if len(g) > 1]
    single_groups = [g for g in groups if len(g) == 1]

    message = "📊 【開源 AI 智慧熱點戰報】\n\n"
    
    # 處理熱點
    if hot_groups:
        for group in hot_groups:
            message += f"🔥 【熱點】（共關聯 {len(group)} 則報導）\n"
            for n_idx in group:
                item = news_list[n_idx]
                title = item.get('title', '無標題').strip()
                summary = item.get('summary', '').strip()
                link = item.get('link', '')
                
                if not summary:
                    summary = title
                if len(summary) > 60:
                    summary = summary[:60] + "..."
                    
                message += f"📌 標題：{title}\n"
                message += f"📝 摘要：{summary}\n"
                if link:
                    message += f"🔗 連結：{link}\n"
                message += "-----------------------\n"
            message += "\n"
            
    # 處理獨立事件
    if single_groups:
        message += "━━━━━━━━━━━━━━━━━━━\n"
        message += "📰 其他（獨立事件） \n\n"
        for g in single_groups:
            n_idx = g[0]
            item = news_list[n_idx]
            title = item.get('title', '無標題').strip()
            summary = item.get('summary', '').strip()
            link = item.get('link', '')
            
            if not summary:
                summary = title
            if len(summary) > 60:
                summary = summary[:60] + "..."
                
            message += f"📌 標題：{title}\n"
            message += f"📝 摘要：{summary}\n"
            if link:
                message += f"🔗 連結：{link}\n"
            message += "-----------------------\n"

    # 7. 發送 Telegram
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        print("Telegram 戰報發送成功！")
    else:
        print(f"發送失敗，錯誤碼: {res.status_code}，訊息: {res.text}")

if __name__ == "__main__":
    main()
