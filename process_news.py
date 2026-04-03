import os
import json
import requests
from ckip_transformers.nlp import CkipWordSegmenter
from sklearn.feature_extraction.text import TfidfVectorizer

def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("未設定 Telegram 憑證，輸出結果如下：\n", text)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    # 1. 讀取 n8n 傳過來的新聞資料
    raw_data = os.environ.get("NEWS_DATA", "[]")
    try:
        all_news = json.loads(raw_data)
    except Exception as e:
        send_telegram("⚠️ 讀取新聞 JSON 失敗。")
        return
        
    if not all_news:
        send_telegram("⚠️ 今日無新新聞資料。")
        return

    # 2. 初始化 CKIP 斷詞器 (若有快取會非常快)
    # level=3 代表使用 BERT-base 模型，準確度最高
    ws_driver = CkipWordSegmenter(level=3)
    
    titles = [news.get('title', '') for news in all_news]
    
    # 3. 執行斷詞 (CKIP 處理)
    ws_results = ws_driver(titles)
    
    # 我們只保留長度大於 1 的詞，並過濾掉無意義的符號
    processed_titles = []
    for sentence in ws_results:
        # 你可以進一步搭配 pos_driver (詞性標記) 只要名詞，這裡先用長度與字串過濾簡化
        words = [w for w in sentence if len(w) > 1 and w.strip()]
        processed_titles.append(" ".join(words))

    # 4. 利用 TF-IDF 演算法抓出每篇新聞的核心關鍵字
    vectorizer = TfidfVectorizer(max_features=10)
    try:
        tfidf_matrix = vectorizer.fit_transform(processed_titles)
        keywords = vectorizer.get_feature_names_out()
    except:
        # 如果新聞太少無法跑 TF-IDF，就直接用原標題
        keywords = []

    # 5. 自動主題分類 (依據關鍵字)
    categorized = {}
    unclassified = []
    
    for idx, news in enumerate(all_news):
        title = news.get('title', '')
        matched = False
        for kw in keywords:
            if kw in title:
                if kw not in categorized:
                    categorized[kw] = []
                categorized[kw].append(news)
                matched = True
                break
        if not matched:
            unclassified.append(news)

    # 6. 組裝 Telegram 漂亮的排版訊息
    msg = "🌟 *【CKIP + NLP 智慧主題分組戰報】*\n\n"
    
    group_idx = 1
    for topic, news_list in categorized.items():
        if len(news_list) <= 1:
            unclassified.extend(news_list)
            continue
        msg += f"📌 *【主題 {group_idx}】關於「{topic}」的報導* ({len(news_list)} 則)\n"
        for n in news_list:
            msg += f" ▫️ [{n.get('media', '新聞')}] {n.get('title')}\n    🔗 [點此閱讀]({n.get('link')})\n"
        msg += "\n"
        group_idx += 1
        
    # 沒被歸類的零星新聞
    # 這裡使用集合(Set)與字典解析來對 dict 進行去重，避免重複發送
    unique_unclassified = list({v['link']: v for v in unclassified if 'link' in v}.values())
    if unique_unclassified:
        msg += f"📌 *【其他即時新聞】*({len(unique_unclassified)} 則)\n"
        for n in unique_unclassified:
            msg += f" ▫️ [{n.get('media', '新聞')}] {n.get('title')}\n    🔗 [點此閱讀]({n.get('link')})\n"

    # 7. 發送
    send_telegram(msg)

if __name__ == "__main__":
    main()
