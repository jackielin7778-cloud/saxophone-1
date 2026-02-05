import streamlit as st
import pandas as pd
import time
import random
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from io import BytesIO

# --- 頁面配置 ---
st.set_page_config(page_title="🎷 薩克斯風吹嘴搜尋拔回系統", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_search_page(url):
    """專門解析搜尋結果列表頁"""
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-8:]))

    try:
        driver = get_driver()
        log(f"🔎 正在掃描搜尋頁面...")
        driver.get(url)
        
        # 滾動頁面確保動態內容載入
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(5)
        
        # Yahoo 搜尋結果的商品容器選取器 (根據 2026 最新結構優化)
        # 每個商品通常包裹在一個特定的 li 或 div 中
        items = driver.find_elements(By.CSS_SELECTOR, 'ul[class*="GeneralList"] li, div[class*="BaseItem"]')
        
        log(f"📦 偵測到該頁面共有 {len(items)} 個商品區塊")

        for item in items:
            try:
                # 1. 抓取標題 (用來判斷樂器)
                title = item.find_element(By.CSS_SELECTOR, 'span[class*="ItemName"], .sc-762bc2d0-5').text
                
                # 2. 抓取價格
                price = item.find_element(By.CSS_SELECTOR, 'span[class*="ItemPrice"], .sc-762bc2d0-10').text
                
                # 3. 抓取賣家
                try:
                    seller = item.find_element(By.CSS_SELECTOR, 'span[class*="SellerName"], .sc-762bc2d0-11').text
                except:
                    seller = "未知賣家"

                # 4. 適用樂器判定邏輯
                t_lower = title.lower()
                instrument = "其他"
                if "alto" in t_lower or "中音" in t_lower: instrument = "中音Alto"
                elif "tenor" in t_lower or "次中音" in t_lower: instrument = "次中音Tenor"
                elif "soprano" in t_lower or "高音" in t_lower: instrument = "高音Soprano"

                all_items.append({
                    "賣方名稱": seller,
                    "商品標題": title,
                    "適用樂器": instrument,
                    "售價": price
                })
            except:
                continue # 略過廣告或資訊不全的區塊

        log(f"✅ 成功拔回 {len(all_items)} 筆有效數據")
        driver.quit()
        return pd.DataFrame(all_items)

    except Exception as e:
        log(f"❌ 錯誤: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🎷 薩克斯風吹嘴搜尋結果「全數拔回」工具")
st.markdown("請在下方貼上 **Yahoo 拍賣搜尋結果頁** 的網址，系統將自動解析整頁商品。")

search_url = st.text_input("輸入搜尋結果網址：", placeholder="https://tw.bid.yahoo.com/search/auction/product?p=...")

if st.button("🚀 開始整頁拔回"):
    if search_url:
        result_df = scrape_search_page(search_url)
        if not result_df.empty:
            st.session_state.search_results = result_df
            st.dataframe(result_df, use_container_width=True)

if 'search_results' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.search_results.to_excel(writer, index=False)
    st.download_button("📥 下載全頁 Excel 報告", output.getvalue(), "yahoo_search_results.xlsx")
