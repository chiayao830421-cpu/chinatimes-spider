import os
import sys
import json
import requests
import ast  # 引入抽象語法樹，用來安全地解析 JS 物件字串
from sentence_transformers import SentenceTransformer, util

def main():
    # 1. 讀取系統參數
    if len(sys.argv) < 4:
        print("錯誤：傳入的參數不足。")
        return
        
    token = sys.argv[1]
    chat_id = sys.argv[2]
    news_data_str = sys.argv[3]
    
    print(f"收到原始資料開頭: {news_data_str[:100]}...") # 方便 debug

    # 2. 超級防呆解析 (使用 ast 繞過 JSON 嚴格的引號限制)
    news_list = []
    try:
        print("嘗試使用 AST 解析類 JavaScript 陣列字串...")
        # ast.literal_eval 可以完美解析 [{title: "..."}] 這種不規範的 JSON 寫法
        news_list = ast.literal_eval(news_data_str)
        
        # 如果解析出來還是字串，再轉一次
        if isinstance(news_list, str):
            news_list = ast.literal_eval(news_list)
            
        print(f"\n🎉 成功接收到資料！總共抓取了 {len(news_list)} 則新聞。")
        
    except Exception as e:
        print(f"AST 解析失敗: {e}")
        print("嘗試啟動最後的 JSON 解析...")
        try:
            news_list = json.loads(news_data_str)
        except Exception as e2:
            print(f"所有解析方法均失敗: {e2}")
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
            
            # 閾值設定 0.65
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
