import streamlit as st
import pandas as pd
import time
import random
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from io import BytesIO

# --- 頁面配置 ---
st.set_page_config(page_title="🎷 薩克斯風吹嘴市場調查系統", layout="wide")

if 'url_list' not in st.session_state:
    st.session_state.url_list = []

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_with_live_logs(urls):
    all_data = []
    
    # 建立一個實時日誌容器
    log_container = st.empty()
    logs = []

    def update_logs(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_container.code("\n".join(logs))

    from datetime import datetime
    
    update_logs("🚀 啟動瀏覽器引擎...")
    try:
        driver = get_driver()
        update_logs("✅ 瀏覽器啟動成功。")
    except Exception as e:
        update_logs(f"❌ 瀏覽器啟動失敗: {str(e)}")
        return pd.DataFrame()

    progress_bar = st.progress(0)
    
    for index, url in enumerate(urls):
        update_logs(f"正在前往: {url}")
        try:
            driver.get(url)
            # 隨機等待
            wait_time = random.uniform(5, 8)
            update_logs(f"等待頁面加載 ({wait_time:.1f}s)...")
            time.sleep(wait_time)
            
            # 取得網頁標題
            title = driver.title
            update_logs(f"網頁標題: {title}")
            
            # 檢查是否被阻擋
            if "Robot Check" in title or "Access Denied" in title or "請確認您的連線" in title:
                update_logs("⚠️ 警告：偵測到機器人驗證，頁面已被封鎖。")
            
            # 嘗試抓取內容
            platform = "蝦皮" if "shopee" in url else "Yahoo拍賣"
            seller = "未知賣家"
            price = "0"
            
            if platform == "蝦皮":
                # 簡單尋找可能包含賣家名稱的標籤
                els = driver.find_elements(By.CSS_SELECTOR, 'span[class*="seller"], ._23_19X')
                if els: seller = els[0].text
                p_els = driver.find_elements(By.CSS_SELECTOR, 'div[class*="price"], .G277_P')
                if p_els: price = p_els[0].text
            else:
                els = driver.find_elements(By.CSS_SELECTOR, '.seller-name, .y-seller-name')
                if els: seller = els[0].text
            
            update_logs(f"解析結果 -> 賣家: {seller}, 價格: {price}")
            
            # 樂器判定
            content = driver.page_source.lower()
            instrument = "其他"
            if "alto" in content or "中音" in content: instrument = "中音Alto"
            elif "tenor" in content or "次中音" in content: instrument = "次中音Tenor"
            elif "soprano" in content or "高音" in content: instrument = "高音Soprano"

            all_data.append({
                "來源平台": platform,
                "賣方名稱": seller,
                "適用樂器": instrument,
                "售價": price,
                "網址": url
            })
            
        except Exception as e:
            update_logs(f"❌ 解析出錯: {str(e)}")
        
        progress_bar.progress((index + 1) / len(urls))
    
    driver.quit()
    update_logs("🏁 爬蟲結束，瀏覽器已關閉。")
    return pd.DataFrame(all_data)

# --- UI 介面 ---
st.title("🎷 薩克斯風吹嘴市場調查 (實時日誌版)")

url_input = st.text_area("請輸入網址 (每行一個)：", height=100)
if st.button("➕ 更新監控清單"):
    st.session_state.url_list = [u.strip() for u in url_input.split("\n") if u.strip()]
    st.success("清單已更新")

if st.session_state.url_list:
    st.write(f"目前監控：{len(st.session_state.url_list)} 個網址")
    
    if st.button("🚀 開始全數拔回"):
        results = scrape_with_live_logs(st.session_state.url_list)
        if not results.empty:
            st.session_state.df_final = results
            st.dataframe(results)

if 'df_final' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.df_final.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 報告", output.getvalue(), "sax_report.xlsx")
