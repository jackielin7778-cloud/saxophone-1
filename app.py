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
st.set_page_config(page_title="🎷 薩克斯風吹嘴搜尋全數拔回", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
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

def identify_brand(title):
    """品牌識別邏輯"""
    brands = {
        "Selmer": ["selmer", "塞爾瑪", "s80", "s90"],
        "Vandoren": ["vandoren", "凡多倫", "萬多林"],
        "Yanagisawa": ["yanagisawa", "柳澤"],
        "Meyer": ["meyer"],
        "Yamaha": ["yamaha", "山葉"],
        "JodyJazz": ["jodyjazz", "jody jazz"],
        "Otto Link": ["otto link", "ottolink"],
        "D'Addario": ["d'addario", "daddario"],
        "Beechler": ["beechler"],
        "Theo Wanne": ["theo wanne"],
        "Berg Larsen": ["berg larsen"]
    }
    t_lower = title.lower()
    for brand, keywords in brands.items():
        if any(k in t_lower for k in keywords):
            return brand
    return "其他/自製"

def scrape_search_page(url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:]))

    try:
        driver = get_driver()
        log("🚀 瀏覽器進入搜尋頁面...")
        driver.get(url)
        
        # 模擬人類向下滾動載入圖片與內容
        for _ in range(2):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)
        
        # 多重 CSS 探針
        selectors = [
            'li[data-item-id]',
            'div[class*="BaseItem"]',
            'ul[class*="GeneralList"] li',
            '.sc-762bc2d0-0'
        ]
        
        items = []
        for s in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, s)
            if len(items) > 5:
                log(f"🎯 探針成功: 使用 [{s}] 抓取")
                break
        
        if not items:
            log("⚠️ 使用保底抓取模式...")
            items = driver.find_elements(By.XPATH, "//div[contains(@class, 'item') or contains(@class, 'product')]")

        log(f"📦 偵測到 {len(items)} 個潛在商品區塊")

        for item in items:
            try:
                # 取得整塊文字進行解析
                raw_text = item.text.strip()
                if not raw_text or "$" not in raw_text:
                    continue
                
                # 1. 解析標題 (通常是第一行或最長的一段)
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                title = lines[0] if lines else "無標題"
                
                # 2. 解析價格
                price_match = re.search(r'\$\s*[0-9,]+', raw_text)
                price = price_match.group() if price_match else "N/A"
                
                # 3. 判斷樂器
                t_lower = title.lower()
                instrument = "其他"
                if "alto" in t_lower or "中音" in t_lower: instrument = "中音Alto"
                elif "tenor" in t_lower or "次中音" in t_lower: instrument = "次中音Tenor"
                elif "soprano" in t_lower or "高音" in t_lower: instrument = "高音Soprano"
                
                # 4. 品牌識別
                brand = identify_brand(title)
                
                # 5. 賣家識別 (嘗試從最後幾行找)
                seller = "商家"
                if len(lines) > 2:
                    # 尋找不包含 $ 且較短的行作為賣家名
                    for l in reversed(lines):
                        if "$" not in l and len(l) < 15:
                            seller = l
                            break

                all_items.append({
                    "品牌": brand,
                    "賣方名稱": seller,
                    "商品資訊": title,
                    "適用樂器": instrument,
                    "售價": price
                })
            except:
                continue

        # 轉成 DataFrame 並移除重複項
        df = pd.DataFrame(all_items).drop_duplicates()
        log(f"✅ 成功拔回 {len(df)} 筆數據")
        driver.quit()
        return df

    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🎷 薩克斯風吹嘴搜尋「全數拔回」系統")
url_input = st.text_input("輸入 Yahoo 搜尋結果網址：", placeholder="https://tw.bid.yahoo.com/search/auction/product?p=...")

if st.button("🚀 執行全頁拔回"):
    if url_input:
        res = scrape_search_page(url_input)
        if not res.empty:
            st.session_state.final_res = res
            st.dataframe(res, use_container_width=True)

if 'final_res' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.final_res.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 調查報告", output.getvalue(), "sax_market_report.xlsx")
