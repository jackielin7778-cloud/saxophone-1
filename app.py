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
st.set_page_config(page_title="薩克斯風吹嘴市場調查系統", layout="wide")

if 'url_list' not in st.session_state:
    st.session_state.url_list = []

def get_driver():
    """強化版：自動偵測 Streamlit Cloud 環境路徑"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 嘗試多個 Linux 下 Chromium 可能的存放路徑
    potential_binary_paths = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/lib/chromium-browser/chromium-browser"
    ]
    
    for path in potential_binary_paths:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break

    # 嘗試多個 Driver 可能的路徑
    potential_driver_paths = [
        "/usr/bin/chromedriver",
        "/usr/lib/chromium-browser/chromedriver"
    ]
    
    driver_executable = None
    for path in potential_driver_paths:
        if os.path.exists(path):
            driver_executable = path
            break

    if driver_executable:
        service = Service(driver_executable)
        return webdriver.Chrome(service=service, options=chrome_options)
    else:
        # 如果都找不到，嘗試讓系統自己找 (最後手段)
        return webdriver.Chrome(options=chrome_options)

def scrape_data(urls):
    all_data = []
    try:
        driver = get_driver()
    except Exception as e:
        st.error(f"❌ 瀏覽器啟動失敗。這通常是 Streamlit 環境尚未完全裝好 packages.txt 導致。錯誤詳情: {e}")
        return pd.DataFrame()

    progress_bar = st.progress(0)
    for index, url in enumerate(urls):
        try:
            driver.get(url)
            time.sleep(random.uniform(5, 8)) 
            page_source = driver.page_source
            
            platform = "蝦皮" if "shopee" in url else "Yahoo拍賣"
            
            # 賣方名稱
            seller_name = "未知賣家"
            try:
                if platform == "蝦皮":
                    seller_name = driver.find_element(By.CSS_SELECTOR, 'span[class*="seller"], ._23_19X').text
                else:
                    seller_name = driver.find_element(By.CSS_SELECTOR, '.name, .seller-name').text
            except:
                seller_name = "需進入網頁確認"

            # 售價
            price = "0"
            price_match = re.search(r'\$\s*[0-9,]+', page_source)
            if price_match:
                price = price_match.group()

            # 適用樂器
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
            st.warning(f"跳過網址: {url}")
        
        progress_bar.progress((index + 1) / len(urls))
    
    driver.quit()
    return pd.DataFrame(all_data)

# --- Streamlit UI ---
st.title("🎷 薩克斯風吹嘴市場調查系統")

new_url = st.text_input("輸入商品網址：", key="url_input")
if st.button("➕ 新增網址"):
    if new_url and new_url not in st.session_state.url_list:
        st.session_state.url_list.append(new_url)

if st.session_state.url_list:
    st.subheader("📋 監控清單")
    for u in st.session_state.url_list:
        st.text(u)

    if st.button("🚀 開始全數拔回"):
        results_df = scrape_data(st.session_state.url_list)
        if not results_df.empty:
            st.session_state.last_result = results_df
            st.dataframe(results_df)

    if 'last_result' in st.session_state:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.last_result.to_excel(writer, index=False)
        st.download_button("📥 下載 Excel 報告", output.getvalue(), "sax_report.xlsx")
