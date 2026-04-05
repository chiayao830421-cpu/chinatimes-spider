import json
from datetime import datetime
import time
import requests

def fetch_udn_politics():
    url = "https://udn.com/api/more?page=1&channelId=2&type=cate_latest_news&cate_id=6638"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://udn.com/news/cate/2/6638",
    }
    
    all_news = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # 兼容 lists 或 data 結構
            all_news = data.get("lists", []) if "lists" in data else data.get("data", [])
            print(f"📡 API 請求成功，原始資料共撈到 {len(all_news)} 則新聞。")
    except Exception as e:
        print(f"💥 API 請求失敗：{e}")
        
    return all_news

# --- 1. 執行爬蟲 ---
news_list = fetch_udn_politics()

# --- 2. 組裝純文字 ---
text_content = ""

# 🚨 防禦力點滿：如果完全沒抓到資料，至少寫下這行，不讓檔案空白！
if not news_list:
    text_content = "title: 無最新新聞\nlink: 無\nsummary: API 抓取失敗或無資料\nmedia: 聯合報\ndate: 無\n"
else:
    # 就算判斷今天日期失敗，我們也至少強迫抓前 10 則最新新聞，絕不留白！
    for item in news_list[:10]: 
        title = item.get("title", "無標題").strip()
        
        # 處理網址
        link = item.get("titleLink", "無網址").strip()
        if link.startswith("/"):
            link = "https://udn.com" + link
            
        # 處理摘要（沒有就拿標題補）
        summary_raw = item.get("paragraph", "")
        if not summary_raw:
            summary_raw = item.get("summary", "")
        summary = summary_raw.strip().replace("\n", " ") if summary_raw else title
        
        media = "聯合報"
        
        # 處理時間
        date = item.get("time", {}).get("dateTime", "")
        if not date:
            date = item.get("time", "無日期")
        date = date.strip()

        # 寫入格式
        text_content += f"title: {title}\n"
        text_content += f"link: {link}\n"
        text_content += f"summary: {summary}\n"
        text_content += f"media: {media}\n"
        text_content += f"date: {date}\n"
        text_content += "-" * 50 + "\n"

# --- 3. 強制寫入檔案 (這段程式碼必須頂格，不能有空格縮排) ---
print("💾 正在強行寫入檔案...")
with open("udn_news.txt", "w", encoding="utf-8") as f:
    f.write(text_content)

print(f"🎉 檔案寫入成功！總字數：{len(text_content)} 字。")
