from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import sys
import re

def run():
    try:
        with sync_playwright() as p:
            print('啟動快閃爬蟲...')
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            print('前往中時政治即時列表...')
            page.goto('https://www.chinatimes.com/realtimenews/260407/?chdtv', wait_until='domcontentloaded', timeout=60000)
            
            # 確保 20 則新聞列表完全渲染出來
            page.wait_for_selector('div.column-wrapper section > ul > li', timeout=15000)
            page.wait_for_timeout(2000)
            
            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'lxml')
            
            # 🌟 抓出所有的 li（包含 1, 4, 5 和中間夾雜的廣告 2, 3）
            all_items = soup.select('div.column-wrapper section > ul > li')
            
            if not all_items:
                print('失敗：找不到新聞區塊。')
                return

            rss_content = '<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n<title>中時政治即時新聞</title>\n'
            
            success_count = 0
            
            for item in all_items:
                # 🌟 1. 抓標題與連結：絕對對齊你給的路徑 div.col > h3 > a
                title_tag = item.select_one('div.col > h3 > a')
                
                # 如果這個 li 裡面沒有這個路徑，代表它是第 2、3 條那種廣告，我們直接跳過！
                if not title_tag:
                    continue 
                
                title = title_tag.text.strip()
                link = title_tag.get('href', '')
                
                if not title or not link:
                    continue
                
                # 補齊完整網址
                if not link.startswith('http'): 
                    link = 'https://www.chinatimes.com' + link
                
                # 🌟 2. 抓時間：對齊你給的第一條與二三條混合結構
                time_tag = item.select_one('div.col > div > time')
                news_date = ""
                
                if time_tag:
                    # 如果有 time 標籤（像第 1 條），先抓 datetime 屬性
                    news_date = time_tag.get('datetime', '')
                    if not news_date:
                        news_date = time_tag.text.strip()
                else:
                    # 如果沒有 time 標籤（像第 2、3 條），直接抓 div.col > div 的文字
                    # 我們指名找 h3 底下的那個 div，最為精準
                    time_div = item.select_one('div.col > h3 + div') 
                    if time_div:
                        news_date = time_div.text.strip()
                
                # 🌟 3. 抓摘要：絕對對齊你給的路徑 div.col > p
                summary_tag = item.select_one('div.col > p')
                summary = summary_tag.text.strip() if summary_tag else "點擊連結查看詳情"
                
                # 🛡️ 備用方案：如果時間真的還是抓不出來，從網址拔日期
                if not news_date and link:
                    date_match = re.search(r'/(\d{8})\d+', link)
                    if date_match:
                        news_date = date_match.group(1) 
                        
                # 清理 XML 特殊字元防爆
                summary = ' '.join(summary.split()).replace('"', "'")
                title = title.replace('"', "'")
                
                rss_content += f'<item>\n<title>{title}</title>\n<link>{link}</link>\n<description>{summary}</description>\n<pubDate>{news_date}</pubDate>\n</item>\n'
                success_count += 1
                
            rss_content += '</channel>\n</rss>'
            
            with open('chinatimes.xml', 'w', encoding='utf-8') as f:
                f.write(rss_content)
                
            print(f'完成！成功抓取 {success_count} 則帶摘要與時間的新聞（已自動跳過廣告）。')

    except Exception as e:
        print(f'嚴重錯誤: {e}')
        sys.exit(1)

if __name__ == '__main__':
    run()
