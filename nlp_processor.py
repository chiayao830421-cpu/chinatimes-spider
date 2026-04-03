import os
import sys
import json
import requests
from sentence_transformers import SentenceTransformer, util

def main():
    # 1. 讀取系統參數
    if len(sys.argv) < 4:
        print("錯誤：傳入的參數不足。")
        return
        
    token = sys.argv[1]
    chat_id = sys.argv[2]
    news_data_str = sys.argv[3]
    
    print(f"收到原始資料開頭: {news_data_str[:50]}...") # 方便 debug

    # 2. 超級防呆解析 JSON
    news_list = []
    try:
        # 第一次解碼
        raw_data = json.loads(news_data_str)
        
        # 如果 n8n 傳過來的是雙重 JSON 字串，我們再解碼一次！
        if isinstance(raw_data, str):
            print("偵測到雙重 JSON 字串，進行二次解碼...")
            raw_data = json.loads(raw_data)
            
        # 判定資料格式
        if isinstance(raw_data, list):
            news_list = raw_data
        elif isinstance(raw_data, dict):
            if "allNews" in raw_data:
                news_list = raw_data["allNews"]
            else:
                news_list = [raw_data]
                    
        print(f"\n🎉 成功接收到資料！總共抓取了 {len(news_list)} 則新聞。")
        
    except Exception as e:
        print(f"解析 JSON 失敗: {e}")
        print("嘗試啟動終極暴力正規化解析...")
        # 如果還是失敗，代表開頭結尾有雜質，用暴力法把頭尾的引號修剪掉
        try:
            trimmed_str = news_data_str.strip('"').replace('\\"', '"')
            news_list = json.loads(trimmed_str)
            print(f"🔥 暴力解析成功！共 {len(news_list)} 則新聞。")
        except Exception as e2:
            print(f"暴力解析依然失敗: {e2}")
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

    message = "📊 【戰報】\n\n"
    
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
            
    if single_groups:
        message += "━━━━━━━━━━━━━━━━━━━\n"
        message += "📰 其他 \n\n"
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
