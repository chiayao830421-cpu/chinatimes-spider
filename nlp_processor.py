import os
import sys
import json
import re
import requests
from sentence_transformers import SentenceTransformer, util

def send_telegram(token, chat_id, text):
    """封裝發送函式"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "HTML",
        "disable_web_page_preview": True 
    }
    return requests.post(url, json=payload)

def main():
    # 1. 讀取參數
    if len(sys.argv) < 4: return
    token, chat_id, news_data_str = sys.argv[1], sys.argv[2], sys.argv[3]
    
    # 2. 物理級欄位擷取
    news_list = []
    blocks = re.findall(r'title\s*:\s*(.*?)\s*,\s*summary\s*:\s*(.*?)\s*,\s*link\s*:\s*(.*?)(?:\s*,\s*media\s*:\s*(.*?))?(?=\s*,\s*title|\s*\}\s*\]|\s*\}\s*,\s*\{|$)', news_data_str, re.DOTALL)
    
    for b in blocks:
        t = b[0].strip('\'" ')
        s = b[1].strip('\'" ')
        l = b[2].strip('\'" }')
        m = b[3].strip('\'" }') if len(b) > 3 and b[3] else "中時新聞網"
        if t:
            news_list.append({"title": t, "summary": s, "link": l, "media": m})

    if not news_list: return

    # 3. 語意向量計算與分組
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

    # 4. 依照「一主題一訊息」發送
    groups.sort(key=len, reverse=True)
    hot_groups = [g for g in groups if len(g) > 1]
    other_groups = [g for g in groups if len(g) == 1]

    # --- A. 發送熱點主題 (每個主題一則訊息) ---
    for i, group in enumerate(hot_groups):
        msg = f"<b>🔥 【主題 {i+1}】(共 {len(group)} 篇關聯報導)</b>\n\n"
        for idx in group:
            n = news_list[idx]
            msg += f"• <b>{n['title']}</b>\n"
            msg += f"  {n['summary'][:120]}...\n"
            msg += f"  🔗 {n['link']}\n"
            msg += f"  🏛️ 媒體：{n['media']}\n\n"
        send_telegram(token, chat_id, msg)

    # --- B. 發送獨立新聞 (全部打包成最後一則，避免過度洗版) ---
    if other_groups:
        msg = "<b>📌 其他獨立新聞亮點</b>\n\n"
        # 限制顯示數量，避免超過 Telegram 訊息長度上限
        for g in other_groups[:15]: 
            n = news_list[g[0]]
            msg += f"• <b>{n['title']}</b>\n"
            msg += f"  🔗 {n['link']}\n"
            msg += f"  🏛️ 媒體：{n['media']}\n\n"
        msg += "💡 <i>其餘新聞已省略...</i>"
        send_telegram(token, chat_id, msg)

if __name__ == "__main__":
    main()
