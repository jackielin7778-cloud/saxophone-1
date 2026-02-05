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
st.set_page_config(page_title="🎷 薩克斯風吹嘴搜尋全數拔回", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 注入更真實的偽裝
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 關鍵：抹除 Selenium 標記
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def scrape_search_page(url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:]))

    try:
        driver = get_driver()
        log("🚀 瀏覽器已偽裝完成，正在進入搜尋頁面...")
        driver.get(url)
        
        # 滾動幾次以觸發動態加載
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(2)
        
        log(f"📄 網頁標題: {driver.title}")

        # --- 2026 Yahoo 拍賣最新多重探針 ---
        # 嘗試找出所有可能的商品容器標籤
        selectors = [
            'ul[class*="GeneralList"] li', 
            'div[class*="BaseItem"]',
            'li[data-item-id]',
            '.sc-762bc2d0-0' # Yahoo 拍賣常用的動態 class
        ]
        
        items = []
        for s in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, s)
            if len(items) > 5: # 如果抓到超過 5 個，代表這個 selector 是對的
                log(f"🎯 使用探針 [{s}] 成功抓取數據")
                break
        
        if not items:
            log("⚠️ 警告：無法自動識別商品區塊，嘗試抓取原始頁面特徵...")
            # 保底方案：抓取所有包含價格符號的區塊
            items = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")

        log(f"📦 偵測到 {len(items)} 個潛在商品區塊")

        for item in items:
            try:
                # 使用相對路徑抓取內容，避免結構變動導致崩潰
                text_content = item.text.replace("\n", " ")
                if "$" not in text_content: continue
                
                # 抓取價格 (正則表達式)
                price_match = re.search(r'\$\s*[0-9,]+', text_content)
                price = price_match.group() if price_match else "N/A"
                
                # 抓取標題與判斷樂器
                title = text_content[:60] # 取前 60 字當作標題
                instrument = "其他"
                t_lower = title.lower()
                if "alto" in t_lower or "中音" in t_lower: instrument = "中音Alto"
                elif "tenor" in t_lower or "次中音" in t_lower: instrument = "次中音Tenor"
                elif "soprano" in t_lower or "高音" in t_lower: instrument = "高音Soprano"

                # 嘗試找賣家 (通常在標題附近)
                seller = "商家"
                # 這裡做一個簡單的賣家偵測，若 item 內有連結，嘗試當作賣家
                all_data = {
                    "賣方名稱": seller,
                    "商品資訊": title,
                    "適用樂器": instrument,
                    "售價": price
                }
                all_items.append(all_data)
            except:
                continue

        # 移除重複項
        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊', '售價'])
        log(f"✅ 成功拔回 {len(df)} 筆不重複數據")
        driver.quit()
        return df

    except Exception as e:
        log(f"❌ 發生異常: {str(e)}")
        return pd.DataFrame()

import re # 補上 regex 模組

# --- UI 介面保持不變 ---
st.title("🎷 薩克斯風吹嘴搜尋「全數拔回」系統")
url_input = st.text_input("輸入 Yahoo 搜尋結果網址：")
if st.button("🚀 執行全頁拔回"):
    if url_input:
        res = scrape_search_page(url_input)
        if not res.empty:
            st.session_state.last_res = res
            st.dataframe(res)

if 'last_res' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.last_res.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel", output.getvalue(), "sax_list.xlsx")
