import json
from datetime import datetime
import time
import requests

def fetch_udn_politics():
    url = "https://udn.com/api/more?page=1&channelId=2&type=cate_latest_news&cate_id=6638"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://udn.com/news/cate/2/6638",
    }
    
    all_news = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            all_news = data.get("lists", []) if "lists" in data else data.get("data", [])
            print(f"📡 API 請求成功，原始資料共撈到 {len(all_news)} 則新聞。")
    except Exception as e:
        print(f"💥 API 請求失敗：{e}")
        
    return all_news

# --- 1. 執行爬蟲 ---
news_list = fetch_udn_politics()

# --- 2. 組裝純文字 ---
text_content = ""

if not news_list:
    text_content = "title: 無最新新聞\nlink: 無\nsummary: API 抓取失敗或無資料\nmedia: 聯合報\ndate: 無\n"
else:
    for item in news_list[:10]: 
        title = item.get("title", "無標題").strip()
        
        # 處理網址
        link = item.get("titleLink", "無網址").strip()
        if link.startswith("/"):
            link = "https://udn.com" + link
            
        # 處理摘要
        summary_raw = item.get("paragraph", "")
        if not summary_raw:
            summary_raw = item.get("summary", "")
        summary = summary_raw.strip().replace("\n", " ") if summary_raw else title
        
        media = "聯合報"
        
        # 🚨 鐵桶防禦：徹底解決字典物件沒有 strip() 的問題
        date_raw = item.get("time", "無日期")
        
        # 如果 time 欄位是個字典，我們就去抓裡面的 dateTime，抓不到就轉成字串
        if isinstance(date_raw, dict):
            date = date_raw.get("dateTime", str(date_raw))
        else:
            date = str(date_raw)
            
        date = date.strip() # 這時候絕對是字串了，100% 不會噴錯！

        # 寫入格式
        text_content += f"title: {title}\n"
        text_content += f"link: {link}\n"
        text_content += f"summary: {summary}\n"
        text_content += f"media: {media}\n"
        text_content += f"date: {date}\n"
        text_content += "-" * 50 + "\n"

# --- 3. 強制寫入檔案 ---
print("💾 正在強行寫入檔案...")
with open("udn_news.txt", "w", encoding="utf-8") as f:
    f.write(text_content)

print(f"🎉 檔案寫入成功！總字數：{len(text_content)} 字。")
