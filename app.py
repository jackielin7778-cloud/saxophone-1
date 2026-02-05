import streamlit as st
import pandas as pd
import time
import random
import re
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from io import BytesIO

# --- 1. 頁面配置 ---
st.set_page_config(page_title="🎷 薩克斯風吹嘴：店家專向調查", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={ua}")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scrape_store_search(base_url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:]))

    # --- 修正搜尋 URL 建構邏輯 ---
    search_query = "吹嘴"
    # 清理網址，確保路徑正確
    base_url = base_url.split('?')[0].rstrip('/')
    # Yahoo 店內搜尋的標準格式
    target_url = f"{base_url}/search/auction/product?p={search_query}"

    try:
        driver = get_driver()
        log(f"🕵️ 正在潛入店家搜尋頁面: {target_url}")
        driver.get(target_url)
        
        # 增加等待時間，確保店家頁面的動態組件載入
        time.sleep(10)
        
        # 執行多次微幅滾動，觸發 Lazy Load
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

        log(f"📄 標題確認: {driver.title}")
        
        # --- 針對店家頁面 (Booth) 的多重探針 ---
        # 1. 嘗試抓取所有商品卡片
        items = driver.find_elements(By.CSS_SELECTOR, 'div[class*="Item__itemContainer"], .item-container, li[data-item-id]')
        
        # 2. 如果沒抓到，嘗試更廣泛的 A 標籤 (商品連結)
        if not items:
            log("⚠️ 標籤探針失效，嘗試深度遍歷商品節點...")
            items = driver.find_elements(By.XPATH, "//div[contains(@class, 'ProductCard')] | //div[contains(@class, 'BaseItem')]")

        log(f"📦 偵測到 {len(items)} 個商品區塊")

        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]
        
        for item in items:
            try:
                raw_text = item.text.replace("\n", " ").strip()
                if "$" not in raw_text: continue
                
                # 提取標題與價格
                # 店家頁面通常標題在 a 標籤內
                try:
                    title_el = item.find_element(By.CSS_SELECTOR, 'span[class*="ItemName"], a[class*="ItemName"]')
                    title = title_el.text
                    link = title_el.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
                except:
                    title = raw_text[:60]
                    link = target_url # 保底
                
                p_match = re.search(r'\$\s*[0-9,]+', raw_text)
                price = p_match.group() if p_match else "N/A"
                
                # 品牌與樂器判定
                brand = "其他"
                for b in brand_list:
                    if b.lower() in title.lower():
                        brand = b
                        break
                
                instrument = "其他"
                if "alto" in title.lower() or "中音" in title.lower(): instrument = "中音Alto"
                elif "tenor" in title.lower() or "次中音" in title.lower(): instrument = "次中音Tenor"

                all_items.append({
                    "品牌": brand,
                    "商品資訊": title,
                    "適用樂器": instrument,
                    "售價": price,
                    "網址": link
                })
            except: continue

        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊'])
        log(f"✅ 調查完成，共拔回 {len(df)} 筆數據")
        driver.quit()
        return df
    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🎷 薩克斯風吹嘴：特定店家調查系統")
store_url = st.text_input("請輸入店家首頁網址：", value="https://tw.bid.yahoo.com/booth/Y9133606367")

if st.button("🚀 執行店內定向調查"):
    if store_url:
        results = scrape_store_search(store_url)
        if not results.empty:
            st.session_state.booth_df = results
            st.dataframe(results, use_container_width=True)
        else:
            st.error("找不到商品。請確認該店家是否有『吹嘴』關鍵字商品，或嘗試更換店家網址。")

if 'booth_df' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.booth_df.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 報告", output.getvalue(), "store_report.xlsx")
