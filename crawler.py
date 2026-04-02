from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import sys

try:
    with sync_playwright() as p:
        print('正在啟動 Chrome 瀏覽器...')
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        print('正在前往中時電子報...')
        page.goto('https://www.chinatimes.com/realtimenews/260407', wait_until='networkidle')
        
        time.sleep(5)
        html = page.content()
        browser.close()
        
        soup = BeautifulSoup(html, 'lxml')
        cards = soup.select('div.articlebox-v, div.category-list div.col, ul.article-list li')[:10]
        print(f'一共偵測到 {len(cards)} 個可能的新聞區塊')
        
        rss_content = '<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n<title>中時政治即時</title>\n'
        
        success_count = 0
        for card in cards:
            try:
                title_tag = card.select_one('h3.title a, .title a, a')
                if not title_tag or not title_tag.text.strip():
                    continue
                    
                title = title_tag.text.strip()
                link = title_tag['href']
                if not link.startswith('http'):
                    link = 'https://www.chinatimes.com' + link
                    
                summary = '無摘要'
                intro_tag = card.select_one('p.intro, p')
                if intro_tag and intro_tag.text.strip():
                    summary = intro_tag.text.strip()
                
                summary = ' '.join(summary.split()).replace('"', "'")
                
                rss_content += f'<item>\n<title>{title}</title>\n<link>{link}</link>\n<description>{summary}</description>\n</item>\n'
                success_count += 1
            except Exception as inner_e:
                print(f'單則解析失敗: {inner_e}')
                continue
                
        rss_content += '</channel>\n</rss>'
        
        if success_count > 0:
            with open('chinatimes.xml', 'w', encoding='utf-8') as f:
                f.write(rss_content)
            print(f'成功！已抓到 {success_count} 則新聞！')
        else:
            print('警告：未成功解析出任何新聞。')
            
except Exception as e:
    print(f'最外層發生錯誤: {e}')
    sys.exit(1) # 只有當最外層徹底失敗時，才發出 exit 1 訊號
