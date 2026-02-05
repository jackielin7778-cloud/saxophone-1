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
    chrome_options.add_argument(f"--window-size={random.randint(1200, 1600)},{random.randint(800, 1000)}")
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

    # --- 關鍵：建構店家搜尋網址 ---
    # 如果網址已經有參數，用 &p=，否則用 ?p=
    search_query = "吹嘴"
    if "?" in base_url:
        target_url = f"{base_url.rstrip('/')}&p={search_query}"
    else:
        target_url = f"{base_url.rstrip('/')}/search/auction/product?p={search_query}"

    try:
        driver = get_driver()
        log(f"🕵️ 進入店家網址並過濾「{search_query}」...")
        driver.get(target_url)
        time.sleep(random.uniform(5, 8))
        
        # 滾動加載
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(2)

        log(f"📄 店家頁面標題: {driver.title}")
        
        # 獲取商品元素 (Yahoo 店家頁面結構)
        # 嘗試多種店家常用的商品容器
        elements = driver.find_elements(By.CSS_SELECTOR, 'li[data-item-id], div[class*="BaseItem"], .item-container')
        
        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]
        
        for el in elements:
            try:
                # 抓取標題與價格
                text = el.text.strip().replace("\n", " ")
                if "$" not in text: continue
                
                # 抓取連結
                link_el = el.find_element(By.TAG_NAME, "a")
                link = link_el.get_attribute("href")
                
                # 價格正則
                p_match = re.search(r'\$\s*[0-9,]+', text)
                price = p_match.group() if p_match else "N/A"
                
                title = text[:80].strip()
                
                # 品牌識別
                brand = "其他"
                for b in brand_list:
                    if b.lower() in title.lower():
                        brand = b
                        break
                
                # 樂器判定
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

        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊', '售價'])
        log(f"✅ 成功從店家拔回 {len(df)} 筆「吹嘴」相關數據")
        driver.quit()
        return df
    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        return pd.DataFrame()

# --- 2. UI 介面 ---
st.title("🎷 薩克斯風吹嘴：特定店家專向調查")
st.markdown("輸入 **店家首頁網址**（例如：`https://tw.bid.yahoo.com/booth/Y12345678`），系統會自動搜尋店內的吹嘴。")

# 預設一個示例店家 (唐川音樂在 Yahoo 的範例路徑結構)
default_store = "https://tw.bid.yahoo.com/booth/Y9133606367"
store_url = st.text_input("店家網址：", value=default_store)

if st.button("🚀 開始店內搜索"):
    if store_url:
        results = scrape_store_search(store_url)
        if not results.empty:
            st.session_state.store_df = results
            st.dataframe(results, use_container_width=True)
        else:
            st.warning("在此店家內找不到相關商品，或 IP 遭暫時阻擋。")

if 'store_df' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.store_df.to_excel(writer, index=False)
    st.download_button("📥 下載店家調查 Excel", output.getvalue(), "store_sax_report.xlsx")
