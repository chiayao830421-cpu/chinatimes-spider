import json
from datetime import datetime
import time
import requests

def fetch_udn_politics_all():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://udn.com/news/cate/2/6638",
    }
    
    all_todays_news = []
    # 取得今天日期 (台灣時間 2026-04-05)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 🚨 改成 range(1, 11)，代表會連續抓 1 到 10 頁！
    for page in range(1, 11):
        url = f"https://udn.com/api/more?page={page}&channelId=2&type=cate_latest_news&cate_id=6638"
        print(f"📡 正在爬取第 {page} 頁...")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"第 {page} 頁請求失敗。")
                break
                
            data = response.json()
            news_list = data.get("lists", []) if "lists" in data else data.get("data", [])
            
            if not news_list:
                print("後面沒有資料了，停止翻頁。")
                break
                
            page_match_count = 0
            for item in news_list:
                date_raw = item.get("time", "")
                date_str = date_raw.get("dateTime", str(date_raw)) if isinstance(date_raw, dict) else str(date_raw)
                
                if today_str in date_str:
                    all_todays_news.append(item)
                    page_match_count += 1
            
            print(f"第 {page} 頁符合今天日期的有 {page_match_count} 則。")
            
            # 如果這一頁完全沒有今天的新聞了，代表更舊的新聞不用看了，直接跳出
            if page_match_count == 0 and len(all_todays_news) > 0:
                print("已經抓完今天的最後一則新聞，停止翻頁！")
                break
                
            time.sleep(1) # 休息 1 秒保護你的 IP
            
        except Exception as e:
            print(f"💥 發生錯誤：{e}")
            break
            
    print(f"🎉 總共抓到 {len(all_todays_news)} 則今天的新聞！")
    return all_todays_news

# --- 1. 執行翻頁爬蟲 ---
all_todays_news = fetch_udn_politics_all()

# --- 2. 組裝純文字 ---
text_content = ""
if not all_todays_news:
    text_content = "title: 無最新新聞\nlink: 無\nsummary: 今日無資料\nmedia: 聯合報\ndate: 無\n"
else:
    for item in all_todays_news:
        title = item.get("title", "無標題").strip()
        link = item.get("titleLink", "無網址").strip()
        if link.startswith("/"):
            link = "https://udn.com" + link
            
        summary_raw = item.get("paragraph", "") or item.get("summary", "")
        summary = summary_raw.strip().replace("\n", " ") if summary_raw else title
        
        date_raw = item.get("time", "無日期")
        date = date_raw.get("dateTime", str(date_raw)) if isinstance(date_raw, dict) else str(date_raw)

        # 🚨 補上剛才漏掉的 media 變數宣告
        media = "聯合報"

        text_content += f"title: {title}\n"
        text_content += f"link: {link}\n"
        text_content += f"summary: {summary}\n"
        text_content += f"media: {media}\n"
        text_content += f"date: {date.strip()}\n"
        text_content += "-" * 50 + "\n"

# --- 3. 強制寫入檔案 ---
with open("udn_news.txt", "w", encoding="utf-8") as f:
    f.write(text_content)
print("💾 檔案寫入成功！")
