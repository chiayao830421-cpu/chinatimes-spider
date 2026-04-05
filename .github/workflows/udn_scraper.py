import json
from datetime import datetime
import time
import requests

def fetch_udn_politics():
    # 1. 填入 UDN API 網址，固定抓第 1 頁
    url = "https://udn.com/api/more?page=1&channelId=2&type=cate_latest_news&cate_id=6638"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://udn.com/news/cate/2/6638",
    }
    
    # 這裡就是剛才報錯、沒被定義的那個關鍵變數！
    all_todays_news = []
    
    # 取得今天日期（例如：2026-04-05）
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 開始爬取 UDN 政治新聞，目標日期：{today_str}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ 請求失敗，狀態碼：{response.status_code}")
            return all_todays_news
            
        data = response.json()
        
        # 解析 UDN 的 JSON 結構
        # 根據 UDN API 特性，新聞列表通常包在 'lists' 或 'data' 裡，這裡做雙重防呆
        news_list = data.get("lists", []) if "lists" in data else data.get("data", [])
        
        for item in news_list:
            # 取得新聞時間
            news_time = item.get("time", {}).get("dateTime", "")
            if not news_time:
                news_time = item.get("time", "")
                
            # 判斷是不是今天的新聞
            if today_str in news_time:
                all_todays_news.append(item)
                
        print(f"🎉 成功撈到 {len(all_todays_news)} 則今天的新聞！")
        
    except Exception as e:
        print(f"💥 發生錯誤：{e}")
        
    return all_todays_news

# --- 執行爬蟲 ---
all_todays_news = fetch_udn_politics()

# --- 💡 將新聞陣列組裝成你指定的 5 個欄位格式 ---
text_content = ""

for item in all_todays_news:
    # 擷取欄位，如果沒有就給預設值
    title = item.get("title", "無標題").strip()
    
    # UDN API 的網址有時是相對路徑，如果是，我們自動幫它補上 domain
    link = item.get("titleLink", "無網址").strip()
    if link.startswith("/"):
        link = "https://udn.com" + link
        
    # 🚨 最關鍵的摘要防呆補位邏輯
    summary_raw = item.get("paragraph", "") # UDN API 常把摘要放在 paragraph
    if not summary_raw:
        summary_raw = item.get("summary", "") # 如果沒有，試試 summary
        
    if not summary_raw: # 如果真的都沒有，直接拿標題來補位
        summary = title
    else:
        summary = summary_raw.strip().replace("\n", " ")
        
    media = "聯合報"
    
    # 取得日期時間
    date = item.get("time", {}).get("dateTime", "無日期").strip()
    if not date:
         date = item.get("time", "無日期").strip()

    # 依照你指定的格式排版
    text_content += f"title: {title}\n"
    text_content += f"link: {link}\n"
    text_content += f"summary: {summary}\n"
    text_content += f"media: {media}\n"
    text_content += f"date: {date}\n"
    text_content += "-" * 50 + "\n"

# 儲存為極輕量的純文字 TXT 檔
with open("udn_news.txt", "w", encoding="utf-8") as f:
    f.write(text_content)

print("🎉 純文字新聞檔 udn_news.txt 已成功產出（摘要無縫補位完成）！")
