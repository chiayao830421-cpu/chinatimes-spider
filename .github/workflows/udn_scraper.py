from datetime import datetime
import json
import time
import requests


def fetch_udn_politics():
    # 1. 填入你提供的真實 API 網址，將 page={page} 設為變數
    base_url = "https://udn.com/api/more?page={page}&channelId=2&type=cate_latest_news&cate_id=6638&totalRecNo=334"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://udn.com/news/cate/2/6638",
    }

    all_todays_news = []
    # 自動獲取今天日期 "2026-04-05"
    today_str = datetime.now().strftime("%Y-%m-%d")

    page = 1
    keep_going = True

    print(f"🚀 開始爬取 UDN 政治新聞，目標日期：{today_str}...")

    while keep_going:
        url = base_url.format(page=page)
        print(f"正在抓取第 {page} 頁 (相當於模擬點擊 More)...")

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                print(f"🛑 達到頁面極限或伺服器拒絕 (HTTP {response.status_code})")
                break

            data = response.json()
            news_list = data.get("lists", [])

            if not news_list:
                print("🛑 這一頁已經沒有資料了。")
                break

            for news in news_list:
                news_time = news.get("time", {}).get("date", "")

                # 🚨 關鍵過濾：只留下今天的新聞
                if news_time.startswith(today_str):
                    link = news.get("titleLink", "")
                    if link.startswith("/"):
                        link = "https://udn.com" + link

                    all_todays_news.append(
                        {
                            "title": news.get("title", "").strip(),
                            "link": link,
                            "time": news_time,
                        }
                    )
                else:
                    # 按照時間排序，一旦看到昨天的新聞，代表今天的新聞全抓完了，安全煞車
                    if news_time and news_time < today_str:
                        print("🎯 偵測到昨天的新聞，停止翻頁！")
                        keep_going = False
                        break

            # 休息 1 秒防止被 UDN 封鎖
            time.sleep(1)
            page += 1

        except Exception as e:
            print(f"💥 發生錯誤: {e}")
            break

    # 2. 剔除重複並按時間排序
    unique_news = list(
        {item["link"]: item for item in all_todays_news}.values()
    )
    unique_news.sort(key=lambda x: x["time"], reverse=True)

    # 3. 存成 JSON 檔，供後續 AI 讀取
    with open("udn_today_news.json", "w", encoding="utf-8") as f:
        json.dump(unique_news, f, ensure_ascii=False, indent=4)

    print(f"\n🎉 任務完成！共抓到 {len(unique_news)} 則今天的政治新聞。")
    print("💾 已儲存至 udn_today_news.json")


if __name__ == "__main__":
    fetch_udn_politics()
