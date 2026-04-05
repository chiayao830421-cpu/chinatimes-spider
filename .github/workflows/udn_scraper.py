# 💡 將新聞陣列組裝成標準的 5 個欄位格式
text_content = ""

for item in all_todays_news:
    title = item.get("title", "無標題").strip()
    link = item.get("url", "無網址").strip()
    
    # 🚨 最關鍵的摘要防呆邏輯
    # 先試著抓摘要，如果沒有（為 None 或空字串），就直接拿標題來補位
    summary_raw = item.get("summary", "") # 先預設空字串
    if not summary_raw: # 如果摘要是 None、空字串、False...
        summary = title # 🚨 核心：用標題取代摘要
    else:
        summary = summary_raw.strip().replace("\n", " ") # 如果有，就洗乾淨
    
    media = "聯合報" # 固定填入媒體名稱
    date = item.get("time", "無日期").strip()
    
    # 依照你指定的格式排版 (用換行隔開每一則)
    text_content += f"title: {title}\n"
    text_content += f"link: {link}\n"
    text_content += f"summary: {summary}\n" # 這裡的摘要一定是 Title 補位過的！
    text_content += f"media: {media}\n"
    text_content += f"date: {date}\n"
    text_content += "-" * 50 + "\n" # 加上分隔線

# 儲存為極輕量的純文字 TXT 檔
with open("udn_news.txt", "w", encoding="utf-8") as f:
    f.write(text_content)

print("🎉 純文字新聞檔 udn_news.txt 已成功產出（摘要已完成防呆補位）！")
