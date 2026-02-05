import streamlit as st
import pandas as pd
import time
import random
import re
import os
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO, StringIO

# --- 日誌設定 ---
log_stream = StringIO()
logging.basicConfig(
    stream=log_stream,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- 頁面配置 ---
st.set_page_config(page_title="🎷 薩克斯風吹嘴市場調查系統", layout="wide")

if 'url_list' not in st.session_state:
    st.session_state.url_list = []
if 'log_history' not in st.session_state:
    st.session_state.log_history = ""

def get_driver():
    logger.info("正在初始化瀏覽器引擎...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            logger.info(f"找到 Chromium 二進位檔: {path}")
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_data(urls):
    all_data = []
    driver = None
    try:
        driver = get_driver()
        wait = WebDriverWait(driver, 10)
        
        progress_bar = st.progress(0)
        for index, url in enumerate(urls):
            logger.info(f"開始爬取第 {index+1} 個網址: {url}")
            try:
                driver.get(url)
                # 隨機延遲對抗反爬
                sleep_time = random.uniform(5, 8)
                time.sleep(sleep_time)
                
                page_title = driver.title
                logger.info(f"網頁標題獲取成功: {page_title}")
                
                # 判定是否被封鎖
                if "Robot Check" in page_title or "請確認您的連線" in page_title or "Access Denied" in page_title:
                    logger.warning("⚠️ 偵測到反爬蟲驗證頁面，無法讀取內容。")
                
                platform = "蝦皮" if "shopee" in url else "Yahoo拍賣"
                seller_name = "未知賣家"
                price = "0"
                
                # --- 嘗試解析 ---
                if platform == "蝦皮":
                    try:
                        # 嘗試抓取賣家
                        seller_el = driver.find_elements(By.CSS_SELECTOR, 'div.V67tSj, ._23_19X, .v_67_Sj')
                        if seller_el:
                            seller_name = seller_el[0].text
                            logger.info(f"找到蝦皮賣家: {seller_name}")
                        
                        price_el = driver.find_elements(By.CSS_SELECTOR, 'div.pqm66z, .G277_P')
                        if price_el:
                            price = price_el[0].text
                    except Exception as e:
                        logger.error(f"蝦皮解析解析失敗: {str(e)}")
                else:
                    try:
                        seller_el = driver.find_elements(By.CSS_SELECTOR, '.seller-name, a[data-curst]')
                        if seller_el:
                            seller_name = seller_el[0].text
                            logger.info(f"找到 Yahoo 賣家: {seller_name}")
                    except Exception as e:
                        logger.error(f"Yahoo 解析失敗: {str(e)}")

                # --- 樂器判定 ---
                content = driver.page_source.lower()
                instrument = "其他/通用"
                if "alto" in content or "中音" in content: instrument = "中音Alto"
                elif "tenor" in content or "次中音" in content: instrument = "次中音Tenor"
                elif "soprano" in content or "高音" in content: instrument = "高音Soprano"

                all_data.append({
                    "來源平台": platform,
                    "賣方名稱": seller_name,
                    "適用樂器": instrument,
                    "售價": price,
                    "網址": url
                })
            except Exception as e:
                logger.error(f"處理網址時發生異常: {str(e)}")
            
            progress_bar.progress((index + 1) / len(urls))
            
    except Exception as e:
        logger.critical(f"驅動程式啟動失敗: {str(e)}")
    finally:
        if driver:
            driver.quit()
            logger.info("瀏覽器已安全關閉。")
    
    return pd.DataFrame(all_data)

# --- Streamlit 介面 ---
st.title("🎷 薩克斯風吹嘴市場調查系統 (Log 調試版)")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🛠️ 數據輸入")
    with st.form("input_form"):
        url_to_add = st.text_input("輸入網址：")
        if st.form_submit_button("新增"):
            if url_to_add and url_to_add not in st.session_state.url_list:
                st.session_state.url_list.append(url_to_add)

    if st.session_state.url_list:
        st.write("監控網址：")
        st.code("\n".join(st.session_state.url_list))
        
        if st.button("🚀 開始全數拔回"):
            df = scrape_data(st.session_state.url_list)
            st.session_state.log_history = log_stream.getvalue()
            if not df.empty:
                st.session_state.df_result = df
                st.success("爬取完成！")
                st.dataframe(df)

with col_right:
    st.subheader("📋 系統運作日誌 (Logs)")
    if st.session_state.log_history:
        st.text_area("請複製下方日誌內容給我分析：", value=st.session_state.log_history, height=400)
        if st.button("🗑️ 清空日誌"):
            st.session_state.log_history = ""
            st.rerun()
    else:
        st.info("執行爬蟲後，日誌將顯示在此處。")

# 下載按鈕
if 'df_result' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.df_result.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 調查報表", output.getvalue(), "sax_report.xlsx")
