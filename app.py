import streamlit as st
import pandas as pd
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from io import BytesIO

# --- 頁面配置 ---
st.set_page_config(page_title="薩克斯風吹嘴市場調查系統", layout="wide")

# 初始化 session_state
if 'url_list' not in st.session_state:
    st.session_state.url_list = []

def get_driver():
    """專為 Streamlit Cloud 環境設計的 Driver 啟動設定"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 指向 Streamlit Cloud 環境中 Chromium 的預設路徑
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # 建立 Service 對象，指向系統環境中的 chromedriver
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_data(urls):
    all_data = []
    try:
        driver = get_driver()
    except Exception as e:
        st.error(f"瀏覽器啟動失敗，請檢查 packages.txt 是否正確安裝。錯誤詳情: {e}")
        return pd.DataFrame()

    progress_bar = st.progress(0)
    for index, url in enumerate(urls):
        try:
            driver.get(url)
            # 隨機延遲，模擬真人行為
            time.sleep(random.uniform(5, 8)) 
            
            page_source = driver.page_source
            
            # 1. 判斷平台
            platform = "蝦皮" if "shopee" in url else "Yahoo拍賣"
            
            # 2. 賣方名稱 (通用模糊搜尋)
            seller_name = "未知賣家"
            try:
                if platform == "蝦皮":
                    seller_name = driver.find_element(By.CSS_SELECTOR, 'span[class*="seller"], ._23_19X').text
                else:
                    seller_name = driver.find_element(By.CSS_SELECTOR, '.name, .seller-name').text
            except:
                seller_name = "需進入網頁確認"

            # 3. 售價解析
            price = "0"
            price_match = re.search(r'\$\s*[0-9,]+', page_source)
            if price_match:
                price = price_match.group()

            # 4. 適用樂器 (關鍵字判定)
            content = page_source.lower()
            if "alto" in content or "中音" in content:
                instrument = "中音Alto"
            elif "tenor" in content or "次中音" in content:
                instrument = "次中音Tenor"
            elif "soprano" in content or "高音" in content:
                instrument = "高音Soprano"
            else:
                instrument = "其他/不限"

            all_data.append({
                "來源平台": platform,
                "賣方名稱": seller_name,
                "適用樂器": instrument,
                "售價": price,
                "商品網址": url
            })
        except Exception as e:
            st.warning(f"跳過無法讀取的網址: {url}")
        
        progress_bar.progress((index + 1) / len(urls))
    
    driver.quit()
    return pd.DataFrame(all_data)

# --- 前台網站介面 ---
st.title("🎷 薩克斯風吹嘴市場調查系統")

# 網址輸入功能
with st.container():
    new_url = st.text_input("輸入新的商品網址 (蝦皮或Yahoo)：", key="url_input")
    if st.button("➕ 新增至調查清單"):
        if new_url:
            if new_url not in st.session_state.url_list:
                st.session_state.url_list.append(new_url)
                st.success("網址已成功紀錄，不會因重新整理而消失。")
            else:
                st.warning("此網址已在清單中。")

# 顯示監控清單
if st.session_state.url_list:
    st.divider()
    st.subheader("📋 目前監控中的網址")
    for i, u in enumerate(st.session_state.url_list):
        st.write(f"{i+1}. {u}")

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ 清空網址"):
            st.session_state.url_list = []
            st.rerun()
    with col2:
        if st.button("🚀 執行全數拔回 (開始爬蟲)"):
            with st.spinner("正在模擬瀏覽器操作中..."):
                results_df = scrape_data(st.session_state.url_list)
                if not results_df.empty:
                    st.session_state.last_result = results_df
                    st.dataframe(results_df)

    # 匯出與下載
    if 'last_result' in st.session_state:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.last_result.to_excel(writer, index=False, sheet_name='吹嘴調查')
        
        st.download_button(
            label="📥 下載 Excel 報告",
            data=output.getvalue(),
            file_name="sax_mouthpiece_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
