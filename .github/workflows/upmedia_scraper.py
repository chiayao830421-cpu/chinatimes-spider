import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def scrape_upmedia():
    # 上報的政治與調查板塊 URL
    urls = [
        "https://www.upmedia.mg/news_list.php?Type=2",   # 政治
        "https://www.upmedia.mg/news_list.php?Type=24"  # 調查（你截圖中的板塊）
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    news_items = []
    current_id = 1
    
    # 用來精準抓取時間的正規表達式 (YYYY-MM-DD HH:MM)
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}')
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 根據你的 DevTools 截圖，精準鎖定 sub-box 區塊
            boxes = soup.select("div.sub-box")
            
            for box in boxes:
                # 1. 抓取標題 (h5.text-truncate-2)
                title_tag = box.select_one("h5.text-truncate-2")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                
                # 2. 抓取連結 (包裹著 h5 的 a 標籤)
                # 尋找帶有特定路徑特徵的 a 標籤
                link_tag = box.select_one('a[href*="/politics/"], a[href*="/news/"]')
                if not link_tag:
                    # 備用方案：直接抓取帶有 href 的第一個 a
                    link_tag = box.find("a", href=True)
                    
                if not link_tag:
                    continue
                    
                href = link_tag["href"]
                # 補全相對路徑網址
                link = f"https://www.upmedia.mg{href}" if href.startswith("/") else href
                
                # 3. 抓取時間與清洗 (p.inv-date)
                date_tag = box.select_one("p.inv-date")
                date_str = ""
                if date_tag:
                    raw_date_text = date_tag.get_text()
                    # 透過 Regex 只抽取出時間部分，自動過濾掉「胡育心」等作者名
                    date_match = date_pattern.search(raw_date_text)
                    if date_match:
                        date_str = date_match.group(0)
                        
                if not date_str:
                    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # 去重檢查（避免政治、調查重複抓到同一則新聞）
                if any(item["link"] == link for item in news_items):
                    continue
                
                # 完美對齊你的 n8n 欄位 Schema
                news_items.append({
                    "id": current_id,
                    "title": title,
                    "link": link,
                    "summary": title,  # 列表頁若無摘要，直接用標題當作摘要餵給 AI
                    "media": "上報",
                    "date": date_str
                })
                current_id += 1
                
        except Exception as e:
            print(f"抓取上報網頁出錯: {e}")
            
    return news_items

if __name__ == "__main__":
    data = scrape_upmedia()
    
    # 輸出成 JSON 檔供 GitHub 託管與 n8n 讀取
    with open("upmedia_news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"成功導出 {len(data)} 則上報新聞至 upmedia_news.json")
