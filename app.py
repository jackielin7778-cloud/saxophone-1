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
st.set_page_config(page_title="🎷 薩克斯風吹嘴：店家強力調查", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size=1920,3000") # 視窗設長，減少滾動次數
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

def scrape_booth_power_scan(base_url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-8:]))

    # --- 關鍵：建構店家搜尋網址 (確保路徑正確) ---
    clean_url = base_url.split('?')[0].rstrip('/')
    if "/search/auction/product" not in clean_url:
        target_url = f"{clean_url}/search/auction/product?p=吹嘴"
    else:
        target_url = clean_url

    try:
        driver = get_driver()
        log(f"🕵️ 正在潛入店家搜尋頁面: {target_url}")
        driver.get(target_url)
        
        # 增加等待與強制渲染時間
        time.sleep(12)
        
        # 模擬人類向下滾動並等待內容加載
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 1.5);")
        time.sleep(3)

        log(f"📄 標題確認: {driver.title}")
        
        # --- 暴力特徵掃描 (不再依賴特定 Class) ---
        # 抓取所有包含「吹嘴」字眼且包含價格標記的區塊
        log("🔍 執行暴力特徵掃描...")
        
        # 我們抓取頁面上所有的 A 標籤 (連結)
        links = driver.find_elements(By.TAG_NAME, "a")
        log(f"📦 偵測到 {len(links)} 個潛在節點，正在篩選「吹嘴」相關內容...")

        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]

        for link_el in links:
            try:
                title = link_el.text.strip()
                # 判定是否為吹嘴商品 (標題長度需適中，且包含吹嘴)
                if "吹嘴" in title and len(title) > 5:
                    url = link_el.get_attribute("href")
                    
                    # 向上尋找父節點來抓取價格
                    # 通常價格會跟標題在同一個容器內
                    parent = link_el.find_element(By.XPATH, "./ancestor::div[contains(., '$')]")
                    price_text = parent.text
                    p_match = re.search(r'\$\s*[0-9,]+', price_text)
                    price = p_match.group() if p_match else "需點入查看"
                    
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
                        "商品資訊": title.split("\n")[0], # 只取第一行標題
                        "適用樂器": instrument,
                        "售價": price,
                        "網址": url
                    })
            except: continue

        # 資料整理
        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊'])
        log(f"✅ 調查完成，成功拔回 {len(df)} 筆數據")
        driver.quit()
        return df
    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🎷 薩克斯風吹嘴：店家調查「強力版」")
store_url = st.text_input("請輸入店家網址：", value="https://tw.bid.yahoo.com/booth/Y9133606367")

if st.button("🚀 開始強力調查"):
    if store_url:
        results = scrape_booth_power_scan(store_url)
        if not results.empty:
            st.session_state.booth_df = results
            st.dataframe(results, use_container_width=True)
        else:
            st.error("掃描結果為 0。請確認：\n1. 店家是否有上架包含『吹嘴』名稱的商品。\n2. 雲端 IP 是否正在被限制訪問。")

if 'booth_df' in st.session_state:
    # 這裡顯示一個預覽
    st.markdown("---")
    st.subheader("📊 調查結果")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.booth_df.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 報告", output.getvalue(), "sax_booth_report.xlsx")
