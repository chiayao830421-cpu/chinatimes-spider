import os
import sys
import json
import re
import requests
from sentence_transformers import SentenceTransformer, util

def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "HTML",
        "disable_web_page_preview": True 
    }
    return requests.post(url, json=payload)

def main():
    if len(sys.argv) < 4: 
        print("參數不足")
        return
    token, chat_id, news_data_str = sys.argv[1], sys.argv[2], sys.argv[3]
    
    print(f"--- 偵測到原始資料 ---")
    print(news_data_str[:200]) # Log 顯示開頭

    # 1. 通殺型正則解析：支援 "title": 或 title: 
    # 邏輯：抓取 title 到 summary 之間、summary 到 link 之間、link 到下一個區塊之間的文字
    news_list = []
    # 修正後的正則，同時相容有引號與無引號的欄位名
    pattern = re.compile(
        r'(?:"?title"?)\s*:\s*(.*?)\s*,\s*'
        r'(?:"?summary"?)\s*:\s*(.*?)\s*,\s*'
        r'(?:"?link"?)\s*:\s*(.*?)\s*(?:,|\}|\]|$)', 
        re.DOTALL
    )
    
    blocks = pattern.findall(news_data_str)
    
    for b in blocks:
        # 去除頭尾引號與雜質
        t = b[0].strip('\'" ')
        s = b[1].strip('\'" ')
        l = b[2].strip('\'" ')
        if t and len(t) > 2: # 確保不是空字串
            news_list.append({"title": t, "summary": s, "link": l, "media": "中時新聞網"})

    print(f"--- 解析結果 ---")
    print(f"成功擷取到 {len(news_list)} 則新聞")

    if not news_list:
        print("❌ 解析後列表為空，請檢查 n8n 傳送格式！")
        return

    # 2. 語意向量分組
    print("正在載入 AI 模型並進行分組...")
    model = SentenceTransformer('shibing624/text2vec-base-chinese')
    sentences = [f"{n['title']} {n['summary']}" for n in news_list]
    embeddings = model.encode(sentences, convert_to_tensor=True)

    groups, processed = [], [False] * len(news_list)
    for i in range(len(news_list)):
        if processed[i]: continue
        curr = [i]
        processed[i] = True
        for j in range(i + 1, len(news_list)):
            if not processed[j] and util.cos_sim(embeddings[i], embeddings[j]).item() > 0.55:
                curr.append(j)
                processed[j] = True
        groups.append(curr)

    # 3. 發送訊息
    groups.sort(key=len, reverse=True)
    hot_groups = [g for g in groups if len(g) > 1]
    other_groups = [g for g in groups if len(g) == 1]

    print(f"準備發送 {len(hot_groups)} 個熱點主題與 1 個綜合訊息")

    for i, group in enumerate(hot_groups):
        msg = f"<b>🔥 【主題 {i+1}】(共 {len(group)} 篇關聯報導)</b>\n\n"
        for idx in group:
            n = news_list[idx]
            msg += f"• <b>{n['title']}</b>\n"
            msg += f"  {n['summary'][:120]}...\n"
            msg += f"  🔗 {n['link']}\n"
            msg += f"  🏛️ 媒體：{n['media']}\n\n"
        send_telegram(token, chat_id, msg)

    if other_groups:
        msg = "<b>📌 其他獨立新聞亮點</b>\n\n"
        for g in other_groups[:15]: 
            n = news_list[g[0]]
            msg += f"• <b>{n['title']}</b>\n"
            msg += f"  🔗 {n['link']}\n\n"
        send_telegram(token, chat_id, msg)
    
    print("✅ 所有流程執行完畢！")

if __name__ == "__main__":
    main()
