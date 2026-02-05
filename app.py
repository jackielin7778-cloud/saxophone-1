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

# --- 頁面配置 ---
st.set_page_config(page_title="🎷 吹嘴調查：雲端生存版", layout="wide")

def get_driver():
    chrome_options = Options()
    # 使用最新無頭模式
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 模擬 iPhone 行動版以降低防火牆戒心
    mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    chrome_options.add_argument(f"user-agent={mobile_ua}")
    chrome_options.add_argument("--window-size=390,844") 
    
    # 隱藏自動化特徵
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # 設定 Streamlit Cloud 上的 Chrome 路徑
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 額外 JS 注入抹除特徵
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scrape_store_mouthpiece(base_url):
    all_items = []
    log_area = st.empty()
    
    # 強制轉換成該店家的「吹嘴」搜尋結果頁
    clean_url = base_url.split('?')[0].rstrip('/')
    target_url = f"{clean_url}/search/auction/product?p=吹嘴"

    try:
        driver = get_driver()
        log_area.code(f"📡 正在嘗試穿透 Yahoo 防火牆... (目標: {target_url})")
        driver.get(target_url)
        
        # 雲端環境需要較長等待時間
        time.sleep(random.randint(15, 20))

        # 模擬滾動
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(2)

        source = driver.page_source
        source_len = len(source)
        
        if source_len < 40000:
            st.warning(f"⚠️ 原始碼長度僅 {source_len} 字元，可能仍被阻擋中。")
        
        # 尋找商品容器 (針對行動版與店家版的多重探針)
        containers = driver.find_elements(By.CSS_SELECTOR, 'li[data-item-id], [class*="Item__itemContainer"], [class*="BaseItem"]')
        
        brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]

        for el in containers:
            try:
                full_text = el.text.strip().replace("\n", " ")
                if "$" in full_text:
                    # 抓取標題 (嘗試從 a 標籤或文字前半段)
                    title = full_text.split("$")[0].strip()[:60]
                    
                    # 抓取價格
                    p_match = re.search(r'\$\s*[0-9,]+', full_text)
                    price = p_match.group() if p_match else "N/A"
                    
                    # 品牌判斷
                    brand = "其他"
                    for b in brand_list:
                        if b.lower() in title.lower():
                            brand = b
                            break
                    
                    all_items.append({
                        "品牌": brand,
                        "商品資訊": title,
                        "售價": price
                    })
            except:
                continue

        driver.quit()
        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊'])
        return df

    except Exception as e:
        st.error(f"❌ 發生異常: {str(e)}")
        if 'driver' in locals(): driver.quit()
        return pd.DataFrame()

# --- 介面 ---
st.title("🎷 薩克斯風吹嘴：店家店內調查器")
st.info("💡 此工具會自動在店家內搜尋「吹嘴」關鍵字。")

store_url = st.text_input("請輸入店家首頁網址：", value="https://tw.bid.yahoo.com/booth/Y9133606367")

if st.button("🚀 執行調查"):
    if store_url:
        with st.spinner("正在抓取數據，請稍候..."):
            results = scrape_store_mouthpiece(store_url)
            
        if not results.empty:
            st.success(f"成功拔回 {len(results)} 筆數據！")
            st.dataframe(results, use_container_width=True)
            
            # Excel 下載
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                results.to_excel(writer, index=False)
            st.download_button("📥 下載 Excel 調查報告", output.getvalue(), "sax_report.xlsx")
        else:
            st.error("目前抓不到任何數據。這代表雲端 IP 仍被 Yahoo 封鎖，或是該店家內無『吹嘴』關鍵字商品。")
