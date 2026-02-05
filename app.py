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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    # 更換更像真人的 User-Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    # 自動偵測路徑
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_data(urls):
    all_data = []
    driver = get_driver()
    wait = WebDriverWait(driver, 15) # 最多等 15 秒
    
    progress_bar = st.progress(0)
    for index, url in enumerate(urls):
        try:
            driver.get(url)
            # 模擬真人滾動頁面，觸發動態載入
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(random.uniform(5, 8)) 
            
            # --- 判斷平台並抓取 ---
            platform = "蝦皮" if "shopee" in url else "Yahoo拍賣"
            seller_name = "未知賣家"
            price = "0"
            
            if platform == "蝦皮":
                try:
                    # 蝦皮賣家名稱可能在不同的 Class 裡
                    seller_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.V67tSj, ._23_19X, .v_67_Sj')))
                    seller_name = seller_el.text
                    # 蝦皮價格
                    price_el = driver.find_element(By.CSS_SELECTOR, 'div.pqm66z, .G277_P')
                    price = price_el.text
                except:
                    seller_name = "偵測到阻擋(需人工)"
            else:
                # Yahoo 拍賣
                try:
                    seller_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.seller-name, a[data-curst]')))
                    seller_name = seller_el.text
                    price_el = driver.find_element(By.CSS_SELECTOR, '.price, .product-price')
                    price = price_el.text
                except:
                    seller_name = "Yahoo解析失敗"

            # --- 適用樂器判定 ---
            page_content = driver.page_source.lower()
            if any(k in page_content for k in ["alto", "中音"]):
                instrument = "中音Alto"
            elif any(k in page_content for k in ["tenor", "次中音"]):
                instrument = "次中音Tenor"
            elif any(k in page_content for k in ["soprano", "高音"]):
                instrument = "高音Soprano"
            else:
                instrument = "其他/通用"

            all_data.append({
                "來源平台": platform,
                "賣方名稱": seller_name,
                "適用樂器": instrument,
                "售價": price,
                "網址": url
            })
        except Exception as e:
            st.error(f"解析 {url} 時發生錯誤")
        
        progress_bar.progress((index + 1) / len(urls))
    
    driver.quit()
    return pd.DataFrame(all_data)

# --- Streamlit UI ---
st.title("🎷 薩克斯風吹嘴市場調查系統")

with st.form("input_form"):
    url_to_add = st.text_input("輸入商品網址：")
    add_btn = st.form_submit_button("新增網址")
    if add_btn and url_to_add:
        if url_to_add not in st.session_state.url_list:
            st.session_state.url_list.append(url_to_add)
            st.success(f"已加入！目前共有 {len(st.session_state.url_list)} 個網址")

if st.session_state.url_list:
    st.write("📋 待爬取清單：")
    st.info("\n".join(st.session_state.url_list))
    
    if st.button("🚀 開始全數拔回"):
        with st.spinner("正在分析網頁結構，請稍候..."):
            df = scrape_data(st.session_state.url_list)
            if not df.empty:
                st.session_state.df_result = df
                st.dataframe(df)
            else:
                st.error("⚠️ 抓取不到資料，可能是被網站防火牆封鎖了 IP。")

    if 'df_result' in st.session_state:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.df_result.to_excel(writer, index=False)
        st.download_button("📥 下載 Excel 調查報表", output.getvalue(), "sax_report.xlsx")

    if st.button("🗑️ 清空紀錄"):
        st.session_state.url_list = []
        if 'df_result' in st.session_state: del st.session_state.df_result
        st.rerun()
