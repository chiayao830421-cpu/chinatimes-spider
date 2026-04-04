html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'lxml')
            # 🌟 【修改】直接把 [:10] 拿掉！只要符合條件的卡片，通通抓進來
            cards = soup.select('.article-list li, .articlebox-v')
            
            if not cards:
                print('失敗：找不到新聞卡片，可能被 Cloudflare 攔截了。')
                return

            # 🌟 讓你知道它在這一頁總共挖到了幾則
            print(f'偵測到畫面上共有 {len(cards)} 則新聞，開始全數解析...')

            rss_content = '<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n<title>中時政治即時</title>\n'
            
            success_count = 0
            for card in cards:
                title_tag = card.select_one('.title a, h3 a')
                if not title_tag: continue
                
                title = title_tag.text.strip()
                link = title_tag['href']
                if not link.startswith('http'): 
                    link = 'https://www.chinatimes.com' + link
                
                # 抓摘要
                summary_tag = card.select_one('.intro, p')
                summary = summary_tag.text.strip() if summary_tag else "點擊連結查看詳情"
                
                # 抓時間
                time_tag = card.select_one('.meta-info time')
                news_date = time_tag['datetime'] if time_tag and time_tag.has_attr('datetime') else ""
                
                # 備用方案（從網址抓日期）
                if not news_date and 'link' in locals() and link:
                    date_match = re.search(r'/(\d{8})\d+', link)
                    if date_match:
                        news_date = date_match.group(1) 
                        
                # 清理 XML 字元防爆
                summary = ' '.join(summary.split()).replace('"', "'")
                title = title.replace('"', "'")
                
                rss_content += f'<item>\n<title>{title}</title>\n<link>{link}</link>\n<description>{summary}</description>\n<pubDate>{news_date}</pubDate>\n</item>\n'
                success_count += 1
                
            rss_content += '</channel>\n</rss>'
            
            with open('chinatimes.xml', 'w', encoding='utf-8') as f:
                f.write(rss_content)
            print(f'完成！成功抓取 {success_count} 則帶摘要與時間的新聞。')
