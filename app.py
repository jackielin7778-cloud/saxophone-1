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
st.set_page_config(page_title="🎷 吹嘴調查：地毯式掃描", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size=1920,3000")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scrape_booth_carpet_scan(base_url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:]))

    # 強制重構 URL
    clean_url = base_url.split('?')[0].rstrip('/')
    target_url = f"{clean_url}/search/auction/product?p=吹嘴"

    try:
        driver = get_driver()
        log(f"🕵️ 地毯式搜索啟動: {target_url}")
        driver.get(target_url)
        time.sleep(12) # 增加穩定性

        # 暴力滾動
        driver.execute_script("window.scrollTo(0, 2000);")
        time.sleep(3)

        # --- 核心邏輯：地毯式掃描 ---
        log("🔍 正在解析 27 個潛在節點內容...")
        
        # 抓取所有可能的商品容器 (Yahoo Booth 常用結構)
        containers = driver.find_elements(By.CSS_SELECTOR, 'li[data-item-id], [class*="Item__itemContainer"], [class*="BaseItem"]')
        
        if not containers:
            # 如果找不到容器，直接抓取所有 A 標籤
            containers = driver.find_elements(By.XPATH, "//a[contains(., '$') or contains(., '吹嘴')]")

        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]

        for idx, el in enumerate(containers):
            try:
                # 抓取該區塊內所有文字
                full_text = el.text.strip().replace("\n", " ")
                
                # 嘗試抓取標題 (從 Title 屬性或 Aria-label 或文字內容)
                title = ""
                try:
                    title_el = el.find_element(By.TAG_NAME, "a")
                    title = title_el.get_attribute("title") or title_el.get_attribute("aria-label") or title_el.text
                    link = title_el.get_attribute("href")
                except:
                    title = full_text[:60]
                    link = target_url

                # 如果標題還是空的或太短，跳過
                if len(title) < 5: continue

                # 價格抓取 (正則表達式)
                p_match = re.search(r'\$\s*[0-9,]+', full_text)
                price = p_match.group() if p_match else "需點擊網址確認"
                
                # 品牌與樂器判定
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
                    "售價": price,
                    "網址": link
                })
            except Exception as e:
                continue

        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊'])
        log(f"✅ 完成！成功從 27 個節點中提取出 {len(df)} 筆有效商品。")
        driver.quit()
        return df
    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# --- UI 介面 ---
st.title("🎷 薩克斯風吹嘴：地毯式調查系統")
store_url = st.text_input("店家網址：", value="https://tw.bid.yahoo.com/booth/Y9133606367")

if st.button("🚀 啟動掃描"):
    if store_url:
        results = scrape_booth_carpet_scan(store_url)
        if not results.empty:
            st.session_state.booth_res = results
            st.dataframe(results, use_container_width=True)
        else:
            st.error("掃描失敗。這通常是標籤選取器完全對不上。請確保網址是正確的店家頁面。")

if 'booth_res' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.booth_res.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 報告", output.getvalue(), "sax_carpet_report.xlsx")
