import os
import sys
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
        print("❌ 參數不足")
        return
    token, chat_id, news_data_str = sys.argv[1], sys.argv[2], sys.argv[3]
    
    print("--- 原始資料開頭 ---")
    print(news_data_str[:300])

    # 1. 暴力字串硬切術 (完全不管 JSON 格式或正則)
    news_list = []
    
    # 用 link 的網址結構作為每一則新聞的切分點
    # 先把資料用 "https://www.chinatimes.com" 切開
    raw_blocks = news_data_str.split("https://www.chinatimes.com")
    
    print(f"初步切分出 {len(raw_blocks)} 個區塊...")
    
    for i in range(len(raw_blocks) - 1):
        # 當前區塊含有前一則新聞的標題和摘要，下一區塊開頭是當前新聞的 link 後半段
        curr_block = raw_blocks[i]
        next_block = raw_blocks[i+1]
        
        # 1. 撈 link (從 next_block 的開頭撈到雙引號結束)
        link_suffix = next_block.split('"')[0].split("'")[0].split("}")[0]
        full_link = "https://www.chinatimes.com" + link_suffix
        
        # 2. 撈 title (在 curr_block 裡找 title: 或 "title": 之後的字)
        title = ""
        if "title" in curr_block:
            # 找到最後一個 title 出現的位置
            t_idx = curr_block.rfind("title")
            # 往後找冒號
            colon_idx = curr_block.find(":", t_idx)
            # 撈出冒號到逗號或引號之間的字
            t_data = curr_block[colon_idx+1:].strip()
            # 移除最外層的引號或括號
            title = t_data.split('",')[0].split("',")[0].split(',"summary')[0].split(",summary")[0]
            title = title.strip('\'" {}[]')
            
        # 3. 撈 summary
        summary = ""
        if "summary" in curr_block:
            s_idx = curr_block.rfind("summary")
            colon_idx = curr_block.find(":", s_idx)
            s_data = curr_block[colon_idx+1:].strip()
            summary = s_data.split('",')[0].split("',")[0].split(',"link')[0].split(",link")[0]
            summary = summary.strip('\'" {}[]')
            
        # 如果沒撈到 summary，就用 title 頂替
        if not summary:
            summary = title
            
        if title and len(title) > 2:
            news_list.append({
                "title": title,
                "summary": summary,
                "link": full_link,
                "media": "中時新聞網"
            })

    print(f"--- 暴力解析結果 ---")
    print(f"成功硬切出 {len(news_list)} 則新聞")

    if not news_list:
        print("❌ 依然無法解析，請查看上方原始資料。")
        return

    # 2. 載入 AI 模型並進行分組
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

    # 3. 按熱點一則則發送
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
