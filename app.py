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

st.set_page_config(page_title="🎷 吹嘴調查：雲端生存版", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # 使用最新的無頭模式，更接近真機
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # --- 核心偽裝：抹除自動化特徵 ---
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 偽裝 UA：使用一個非常具體的真實版本
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={ua}")
    
    # 設定一個較大的視窗，防止 Lazy Load 判定
    chrome_options.add_argument("--window-size=1920,1080")

    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # --- JavaScript 注入：深度抹除指紋 ---
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-TW', 'zh']
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """
    })
    return driver

def scrape_cloud_final_attempt(base_url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-8:]))

    # 確保搜尋路徑正確
    clean_url = base_url.split('?')[0].rstrip('/')
    target_url = f"{clean_url}/search/auction/product?p=吹嘴"

    try:
        driver = get_driver()
        log(f"🕵️ 正在嘗試穿透 Yahoo 防火牆...")
        
        # 偽裝：先去 Google 再去 Yahoo (Referrer 偽裝)
        driver.get("https://www.google.com")
        time.sleep(2)
        
        driver.get(target_url)
        
        # 增加隨機等待，避免被發現是固定頻率
        wait_time = random.randint(15, 25)
        log(f"⏳ 靜候數據渲染中 ({wait_time}s)...")
        time.sleep(wait_time)

        # 暴力滾動
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)

        source = driver.page_source
        log(f"📦 原始碼長度: {len(source)} 字元")

        # 判定是否成功取得內容
        if len(source) < 50000:
            log("⚠️ 警告：內容長度異常，可能仍被阻擋。")
        
        # 尋找所有商品容器
        # 店家搜尋結果頁面的商品通常在 div.GridItem__gridItem___ 或類似標籤
        containers = driver.find_elements(By.CSS_SELECTOR, 'div[class*="Item__itemContainer"], li[data-item-id], [class*="BaseItem"]')
        
        log(f"🔍 找到 {len(containers)} 個商品塊")

        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]

        for el in containers:
            try:
                title = el.find_element(By.CSS_SELECTOR, '[class*="ItemName"]').text
                price = el.find_element(By.CSS_SELECTOR, '[class*="ItemPrice"]').text
                
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
        log(f"❌ 異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# UI 介面
st.title("🎷 吹嘴調查：雲端生存版")
store_url = st.text_input("店家網址：", value="https://tw.bid.yahoo.com/booth/Y9133606367")

if st.button("🚀 啟動調查"):
    results = scrape_cloud_final_attempt(store_url)
    if not results.empty:
        st.dataframe(results, use_container_width=True)
        # 提供下載
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            results.to_excel(writer, index=False)
        st.download_button("📥 下載報告", output.getvalue(), "sax_report.xlsx")
    else:
        st.error("目前雲端 IP 遭 Yahoo 封鎖，請稍候再試。")
