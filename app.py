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

# --- 1. 頁面初始化 ---
st.set_page_config(page_title="🎷 薩克斯風吹嘴市調系統", layout="wide")

if 'url_list' not in st.session_state:
    st.session_state.url_list = []

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def scrape_engine(urls):
    all_data = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:]))

    try:
        driver = get_driver()
        log("🚀 瀏覽器啟動成功。")
    except Exception as e:
        log(f"❌ 驅動異常: {str(e)}")
        return pd.DataFrame()

    progress_bar = st.progress(0)
    for index, url in enumerate(urls):
        try:
            log(f"🔎 正在抓取 ({index+1}/{len(urls)})...")
            driver.get(url)
            
            load_time = random.uniform(5, 7)
            time.sleep(load_time)
            
            title = driver.title
            log(f"📄 標題: {title[:30]}...")

            platform = "蝦皮" if "shopee" in url else "Yahoo拍賣"
            seller = "未知賣家"
            price = "尚未擷取"
            
            # --- 強化解析邏輯 ---
            if platform == "Yahoo拍賣":
                # 嘗試多種可能的賣家名稱 CSS
                seller_selectors = [
                    'a[data-curst]', 
                    '.yui3-u-1 .name', 
                    'div[class*="SellerName"]', 
                    '.seller-name',
                    'span[class*="SellerName"]'
                ]
                for selector in seller_selectors:
                    els = driver.find_elements(By.CSS_SELECTOR, selector)
                    if els and els[0].text.strip():
                        seller = els[0].text.strip()
                        break
                
                # 嘗試抓取價格 (Yahoo 的價格通常在特定的 class 或包含 $ 的字串)
                price_selectors = ['.price', '.product-price', 'span[class*="Price"]']
                for selector in price_selectors:
                    p_els = driver.find_elements(By.CSS_SELECTOR, selector)
                    if p_els:
                        price = p_els[0].text.strip()
                        break
                if price == "尚未擷取":
                    # 正則表達式保底抓取價格
                    price_match = re.search(r'\$\s*[0-9,]+', driver.page_source)
                    if price_match: price = price_match.group()

            elif platform == "蝦皮":
                s_els = driver.find_elements(By.CSS_SELECTOR, 'span.V67tSj, ._23_19X, .official-shop-label__name')
                if s_els: seller = s_els[0].text
                p_match = re.search(r'\$\s*[0-9,]+', driver.page_source)
                if p_match: price = p_match.group()

            # --- 樂器判定 ---
            content = driver.page_source.lower()
            instrument = "其他/通用"
            if "alto" in content or "中音" in content: instrument = "中音Alto"
            elif "tenor" in content or "次中音" in content: instrument = "次中音Tenor"
            elif "soprano" in content or "高音" in content: instrument = "高音Soprano"

            all_data.append({
                "賣方名稱": seller,
                "適用樂器": instrument,
                "售價": price,
                "來源平台": platform,
                "商品網址": url
            })
            log(f"✅ 解析完成: {seller} / {price}")

        except Exception as e:
            log(f"❌ 錯誤: {str(e)}")
        
        progress_bar.progress((index + 1) / len(urls))

    driver.quit()
    return pd.DataFrame(all_data)

# --- 2. UI 介面 ---
st.title("🎷 薩克斯風吹嘴市場調查系統")

url_input = st.text_area("請輸入網址：", height=100)
if st.button("➕ 更新清單"):
    st.session_state.url_list = [u.strip() for u in url_input.split("\n") if u.strip()]

if st.session_state.url_list:
    if st.button("🚀 開始全數拔回"):
        df = scrape_engine(st.session_state.url_list)
        if not df.empty:
            st.session_state.df_results = df
            st.dataframe(df)

if 'df_results' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.df_results.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 調查報告", output.getvalue(), "sax_report.xlsx")
