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
st.set_page_config(page_title="🎷 薩克斯風吹嘴搜尋拔回 (預設網址版)", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 隨機視窗大小與 UA 偽裝
    chrome_options.add_argument(f"--window-size={random.randint(1200, 1920)},{random.randint(800, 1080)}")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
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

def scrape_search_enhanced(url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:]))

    try:
        driver = get_driver()
        log("🕵️ 調查員已就位，正在執行潛入行動...")
        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': {'Referer': 'https://www.google.com/'}})
        driver.get(url)
        
        # 模擬人類滾動
        for i in range(3):
            driver.execute_script(f"window.scrollBy(0, {random.randint(500, 800)});")
            time.sleep(random.uniform(2, 3))

        log(f"📄 偵測標題: {driver.title}")
        
        # 暴力掃描所有商品塊
        elements = driver.find_elements(By.XPATH, "//li | //div[contains(@class, 'item')]")
        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler"]
        
        for el in elements:
            try:
                txt = el.text.strip().replace("\n", " ")
                if "$" in txt and len(txt) > 20:
                    p_match = re.search(r'\$\s*[0-9,]+', txt)
                    price = p_match.group() if p_match else "N/A"
                    title = txt[:80].strip()
                    
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
                        "商品標題": title,
                        "適用樂器": instrument,
                        "售價": price
                    })
            except: continue

        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品標題', '售價'])
        log(f"✅ 成功拔回 {len(df)} 筆數據")
        driver.quit()
        return df
    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        return pd.DataFrame()

# --- 2. UI 介面 ---
st.title("🎷 薩克斯風吹嘴市調工具")

# 設定預設網址
default_url = "https://tw.bid.yahoo.com/search/auction/product?p=%E8%96%A9%E5%85%8B%E6%96%AF%E9%A2%A8%E5%90%B9%E5%98%B4"
search_url = st.text_input("輸入 Yahoo 搜尋結果網址：", value=default_url)

if st.button("🚀 執行潛入調查"):
    if search_url:
        results = scrape_search_enhanced(search_url)
        if not results.empty:
            st.session_state.final_df = results
            st.dataframe(results, use_container_width=True)
        else:
            st.error("調查結果為 0。這代表雲端 IP 目前仍被封鎖中，請過段時間再試。")

if 'final_df' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.final_df.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 調查報告", output.getvalue(), "sax_report.xlsx")
