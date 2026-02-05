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

st.set_page_config(page_title="🎷 吹嘴調查：行動版偽裝突破", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # --- 行動版偽裝：模擬 iPhone 14 ---
    mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    chrome_options.add_argument(f"user-agent={mobile_ua}")
    chrome_options.add_argument("--window-size=390,844") # iPhone 螢幕尺寸
    
    # 抹除自動化特徵
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 注入行動端觸控與 WebDriver 抹除
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scrape_mobile_attempt(base_url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-8:]))

    # --- 關鍵：強制轉換為行動版網址 ---
    # 範例：https://tw.bid.yahoo.com/booth/Y9133606367 -> https://tw.bid.yahoo.com/booth/Y9133606367
    # Yahoo 的行動版有時會自動跳轉，我們手動確保路徑包含店內搜尋
    clean_url = base_url.split('?')[0].rstrip('/')
    target_url = f"{clean_url}/search/auction/product?p=吹嘴"

    try:
        driver = get_driver()
        log("📱 啟動 iPhone 模式潛入調查...")
        driver.get(target_url)
        
        # 增加隨機等待
        wait_time = random.randint(15, 20)
        log(f"⏳ 等待行動版網頁渲染 ({wait_time}s)...")
        time.sleep(wait_time)

        # 多次小幅滑動
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(2)

        source = driver.page_source
        log(f"📦 原始碼長度: {len(source)} 字元")

        # 行動版網頁通常使用 [class*="ProductItem"] 或 [data-testid]
        # 使用廣域探針尋找包含價格的商品塊
        containers = driver.find_elements(By.XPATH, "//li | //div[contains(@class, 'Item')] | //div[contains(@class, 'Product')]")
        
        log(f"🔍 偵測到 {len(containers)} 個潛在商品區塊")

        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]

        for el in containers:
            try:
                txt = el.text.replace("\n", " ").strip()
                if "$" in txt and len(txt) > 10:
                    # 抓取標題 (嘗試尋找 A 標籤或直接取前 50 字)
                    try:
                        title = el.find_element(By.XPATH, ".//a").get_attribute("title") or el.text.split("$")[0].strip()
                    except:
                        title = txt.split("$")[0].strip()
                    
                    if len(title) < 4: continue

                    # 抓取價格
                    p_match = re.search(r'\$\s*[0-9,]+', txt)
                    price = p_match.group() if p_match else "N/A"
                    
                    brand = "其他"
                    for b in brand_list:
                        if b.lower() in title.lower():
                            brand = b
                            break
                    
                    all_items.append({
                        "品牌": brand,
                        "商品資訊": title,
                        "售價": price,
                        "網址": target_url
                    })
            except: continue

        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊'])
        log(f"✅ 成功提取 {len(df)} 筆數據")
        driver.quit()
        return df
        
    except Exception as e:
        log(f"❌ 嚴重異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🎷 吹嘴調查：行動版偽裝系統")
st.info("💡 透過模擬 iPhone 行動版網頁，嘗試避開桌機版的 IP 封鎖。")

default_store = "https://tw.bid.yahoo.com/booth/Y9133606367"
store_url = st.text_input("店家網址：", value=default_store)

if st.button("🚀 啟動行動版偽裝掃描"):
    if store_url:
        results = scrape_mobile_attempt(store_url)
        if not results.empty:
            st.dataframe(results, use_container_width=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                results.to_excel(writer, index=False)
            st.download_button("📥 下載報告", output.getvalue(), "mobile_sax_report.xlsx")
        else:
            st.error("掃描失敗。這代表 Yahoo 已對該伺服器 IP 進行全站屏蔽。")
