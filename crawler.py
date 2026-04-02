from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import sys

def run():
    try:
        with sync_playwright() as p:
            print('啟動快閃爬蟲...')
            browser = p.chromium.launch(headless=True)
            # 模擬更真實的 Mac Chrome 環境
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # 關鍵：不等 networkidle，只要 DOM 出來就開始
            print('前往中時政治版...')
            try:
                page.goto('https://www.chinatimes.com/realtimenews/260407', wait_until='domcontentloaded', timeout=60000)
                # 只等最關鍵的新聞標題出現，一旦出現立刻抓取
                page.wait_for_selector('.article-list', timeout=15000)
            except Exception as e:
                print(f'頁面載入稍慢，嘗試直接解析內容... ({e})')

            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'lxml')
            # 這是目前中時最準確的卡片選擇器
            cards = soup.select('.article-list li, .articlebox-v')[:10]
            
            if not cards:
                print('失敗：找不到新聞卡片，可能被 Cloudflare 攔截了。')
                return

            rss_content = '<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n<title>中時政治即時</title>\n'
            
            success_count = 0
            for card in cards:
                title_tag = card.select_one('.title a, h3 a')
                if not title_tag: continue
                
                title = title_tag.text.strip()
                link = title_tag['href']
                if not link.startswith('http'): link = 'https://www.chinatimes.com' + link
                
                # 抓摘要：中時的摘要通常在 .intro 或 .vertical-box-text
                summary_tag = card.select_one('.intro, p')
                summary = summary_tag.text.strip() if summary_tag else "點擊連結查看詳情"
                
                # 清理文字防止 XML 壞掉
                summary = ' '.join(summary.split()).replace('"', "'")
                
                rss_content += f'<item>\n<title>{title}</title>\n<link>{link}</link>\n<description>{summary}</description>\n</item>\n'
                success_count += 1
                
            rss_content += '</channel>\n</rss>'
            
            with open('chinatimes.xml', 'w', encoding='utf-8') as f:
                f.write(rss_content)
            print(f'完成！成功抓取 {success_count} 則帶摘要的新聞。')

    except Exception as e:
        print(f'嚴重錯誤: {e}')
        sys.exit(1)

if __name__ == '__main__':
    run()
