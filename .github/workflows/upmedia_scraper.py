import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

def fetch_upmedia_politics_all():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    
    all_todays_news = []
    # 取得今天日期 (台灣時間 2026 年)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 抓取政治（Type=2）與調查（Type=24）板塊
    urls = [
        "https://www.upmedia.mg/news_list.php?Type=2",
        "https://www.upmedia.mg/news_list.php?Type=24"
    ]
    
    # 用來比對日期的 Regex (YYYY-MM-DD)
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    # 用來抓取完整時間的 Regex (YYYY-MM-DD HH:MM)
    full_date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}')
    
    for url in urls:
        board_name = "政治" if "Type=2" in url else "調查"
        print(f"📡 正在爬取上報【{board_name}】板塊...")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"💥 該板塊請求失敗。")
                continue
                
            soup = BeautifulSoup(response.text, "html.parser")
            # 依據 DevTools 截圖，精準定位卡片主體
            boxes = soup.select("div.sub-box")
            
            page_match_count = 0
            for box in boxes:
                # 1. 檢查日期 (p.inv-date)
                date_tag = box.select_one("p.inv-date")
                if not date_tag:
                    continue
                    
                date_text = date_tag.get_text()
                date_match = date_pattern.search(date_text)
                if not date_match:
                    continue
                    
                news_date_str = date_match.group(0)
                
                # 🚨 核心邏輯：如果日期符合今天，才進行抓取！
                if today_str == news_date_str:
                    # 抓取標題 (h5.text-truncate-2)
                    title_tag = box.select_one("h5.text-truncate-2")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    
                    # 抓取連結 (包裹著 h5 的 a 標籤)
                    a_tag = title_tag.find_parent("a")
                    if not a_tag or 'href' not in a_tag.attrs:
                        continue
                    href = a_tag["href"]
                    link = f"https://www.upmedia.mg{href}" if href.startswith("/") else href
                    
                    # 提取包含時間的完整字串
                    full_date_match = full_date_pattern.search(date_text)
                    full_date = full_date_match.group(0) if full_date_match else news_date_str
                    
                    # 網址去重檢查（避免政治、調查重複抓到同一則焦點新聞）
                    if any(item["link"] == link for item in all_todays_news):
                        continue
                        
                    all_todays_news.append({
                        "title": title,
                        "link": link,
                        "date": full_date
                    })
                    page_match_count += 1
            
            print(f"📊 該頁面符合今天日期的有 {page_match_count} 則。")
            time.sleep(1) # 休息 1 秒保護 IP
            
        except Exception as e:
            print(f"💥 發生錯誤：{e}")
            continue
            
    print(f"🎉 總共抓到 {len(all_todays_news)} 則今天的新聞！")
    return all_todays_news

# --- 1. 執行翻頁爬蟲 ---
all_todays_news = fetch_upmedia_politics_all()

# --- 2. 組裝純文字 (完全複製你 UDN 的格式) ---
text_content = ""
if not all_todays_news:
    text_content = "title: 無最新新聞\nlink: 無\nsummary: 今日無資料\nmedia: 上報\ndate: 無\n"
else:
    for item in all_todays_news:
        title = item.get("title", "無標題").strip()
        link = item.get("link", "無網址").strip()
        
        # 上報列表頁無摘要，直接依你的習慣用 title 代入
        summary = title
        
        date = item.get("date", "無日期")
        media = "上報"

        text_content += f"title: {title}\n"
        text_content += f"link: {link}\n"
        text_content += f"summary: {summary}\n"
        text_content += f"media: {media}\n"
        text_content += f"date: {date.strip()}\n"
        text_content += "-" * 50 + "\n"

# --- 3. 強制寫入檔案 ---
with open("upmedia_news.txt", "w", encoding="utf-8") as f:
    f.write(text_content)
print("💾 上報檔案寫入成功！")
