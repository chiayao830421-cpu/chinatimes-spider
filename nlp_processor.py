import os
import sys
import json
import requests
from sentence_transformers import SentenceTransformer, util

def main():
    # 改從系統參數（sys.argv）直接讀取，完全不怕 YAML 空格錯
    if len(sys.argv) < 4:
        print("錯誤：傳入的參數不足。")
        return
        
    token = sys.argv[1]
    chat_id = sys.argv[2]
    news_data_str = sys.argv[3]
    
    if not token or token == "${{ secrets.TELEGRAM_TOKEN }}":
        print("缺少 Telegram Token 或 GitHub Secrets 讀取失敗")
        return
        
    if not chat_id:
        print("缺少 Telegram Chat ID")
        return
        
    if not news_data_str:
        print("沒有收到任何新聞資料")
        return

    # --- 底下的 1 到 5 步驟完全不用變，維持上一輪給你的代碼即可 ---
    try:
        raw_data = json.loads(news_data_str)
        # (後面接原本的代碼...)
