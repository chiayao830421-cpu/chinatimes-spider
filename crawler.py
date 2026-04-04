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
            # 使用你指定的標準即時網址
            page.goto('https://www.chinatimes.com/realtimenews/260407/?chdtv', wait_until='domcontentloaded', timeout=60000)
            
            # 給它 2 秒讓 20 則新聞的 JavaScript 完全渲染出來
            page.wait_for_timeout(2000)
            
            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'lxml')
            
            # 🌟 【終極放寬選擇器】
            # 我們不再限定 .article-list li，而是直接抓取所有可能包含新聞的區塊
            cards = soup.select('.article-list li, .articlebox-v, .col .item')
            
            if not cards:
                print('失敗：找不到新聞卡片，可能被 Cloudflare 攔截了。')
                return

            rss_content = '<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n<title>中時政治即時新聞</title>\n'
            
            success_count = 0
            seen_links = set() # 防止首頁重複抓取
            
            for card in cards:
                title_tag = card.select_one('.title a, h3 a, a')
                if not title_tag: continue
                
                title = title_tag.text.strip()
                link = title_tag.get('href', '')
                
                # 過濾掉無效的文字或空連結
                if not title or not link or 'category' in link: 
                    continue
                
                # 補全網址
                if not link.startswith('http'): 
                    link = 'https://www.chinatimes.com' + link
                
                # 去重
                if link in seen_links:
                    continue
                seen_links.add(link)
                
                # 抓摘要
                summary_tag = card.select_one('.intro, p, .vertical-box-text')
                summary = summary_tag.text.strip() if summary_tag else "點擊連結查看詳情"
                
                # 抓時間
                time_tag = card.select_one('time, .time')
                news_date = time_tag['datetime'] if time_tag and time_tag.has_attr('datetime') else ""
                
                # 備用方案：從網址抓日期
                if not news_date and link:
                    date_match = re.search(r'/(\d{8})\d+', link)
                    if date_match:
                        news_date = date_match.group(1) 
                        
                # 清理 XML 字元
                summary = ' '.join(summary.split()).replace('"', "'")
                title = title.replace('"', "'")
                
                rss_content += f'<item>\n<title>{title}</title>\n<link>{link}</link>\n<description>{summary}</description>\n<pubDate>{news_date}</pubDate>\n</item>\n'
                success_count += 1
                
            rss_content += '</channel>\n</rss>'
            
            with open('chinatimes.xml', 'w', encoding='utf-8') as f:
                f.write(rss_content)
            print(f'完成！成功抓取 {success_count} 則帶摘要與時間的新聞。')

    except Exception as e:
        print(f'嚴重錯誤: {e}')
        sys.exit(1)

if __name__ == '__main__':
    run()
