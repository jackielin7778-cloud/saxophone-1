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
from io import BytesIO

st.set_page_config(page_title="🎷 吹嘴調查：原始碼暴力掃描", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size=1920,5000")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_source_code_scan(base_url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-8:]))

    clean_url = base_url.split('?')[0].rstrip('/')
    target_url = f"{clean_url}/search/auction/product?p=吹嘴"

    try:
        driver = get_driver()
        log(f"🕵️ 暴力掃描啟動: {target_url}")
        driver.get(target_url)
        
        # 強制等待與多次深度滾動，確保 JavaScript 執行完畢
        for i in range(5):
            driver.execute_script(f"window.scrollTo(0, {i * 1000});")
            time.sleep(3)

        source = driver.page_source
        log(f"📦 原始碼長度: {len(source)} 字元，開始正則解析...")

        # --- 正則表達式：直接從 JSON 數據或標籤屬性中挖取 ---
        # 尋找包含「吹嘴」的標題、價格以及商品 ID 的模式
        # 這是 Yahoo 2026 年底層數據常用的 JSON 結構特徵
        patterns = [
            # 模式 1: 抓取標題與價格 (針對動態加載的 JSON 區塊)
            r'\"title\":\"([^\"]*吹嘴[^\"]*)\".*?\"ecPrice\":\"(\d+)\"',
            # 模式 2: 針對 HTML 屬性的保底抓取
            r'title=\"([^\"]*吹嘴[^\"]*)\".*?\$([0-9,]+)'
        ]

        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]

        for pattern in patterns:
            matches = re.findall(pattern, source)
            for title, price in matches:
                brand = "其他"
                for b in brand_list:
                    if b.lower() in title.lower():
                        brand = b
                        break
                
                instrument = "其他"
                if any(k in title.lower() for k in ["alto", "中音"]): instrument = "中音Alto"
                elif any(k in title.lower() for k in ["tenor", "次中音"]): instrument = "次中音Tenor"

                all_items.append({
                    "品牌": brand,
                    "商品資訊": title,
                    "適用樂器": instrument,
                    "售價": f"${price}",
                    "網址": target_url # 暴力掃描較難精準匹配個別網址，先給予搜尋頁網址
                })

        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊'])
        log(f"✅ 暴力掃描完成！成功提取出 {len(df)} 筆商品。")
        driver.quit()
        return df
    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# UI 介面
st.title("🎷 吹嘴調查：原始碼暴力掃描版")
store_url = st.text_input("店家網址：", value="https://tw.bid.yahoo.com/booth/Y9133606367")

if st.button("🚀 啟動暴力調查"):
    if store_url:
        results = scrape_source_code_scan(store_url)
        if not results.empty:
            st.session_state.brute_res = results
            st.dataframe(results, use_container_width=True)
        else:
            st.error("暴力掃描也失敗。這代表該店家在雲端環境下完全封鎖了內容渲染。")

if 'brute_res' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.brute_res.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 報告", output.getvalue(), "sax_brute_report.xlsx")
