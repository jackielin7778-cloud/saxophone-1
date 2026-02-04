import streamlit as st
import pandas as pd
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from io import BytesIO

# --- 初始化設定 ---
st.set_page_config(page_title="薩克斯風吹嘴市場調查系統", layout="wide")

if 'url_list' not in st.session_state:
    st.session_state.url_list = []

def get_driver():
    """初始化雲端環境專用的 Chrome Driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # 偽裝成真人瀏覽器
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 自動安裝並啟動 Driver
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_data(urls):
    all_data = []
    driver = get_driver()
    
    progress_bar = st.progress(0)
    for index, url in enumerate(urls):
        try:
            driver.get(url)
            # 隨機延遲 5-10 秒，對抗電商偵測
            time.sleep(random.uniform(5, 10)) 
            
            # 獲取頁面標題與內容
            page_title = driver.title
            page_source = driver.page_source
            
            # --- 賣方名稱解析 ---
            # 蝦皮與 Yahoo 結構常變，這裡使用更具彈性的尋找方式
            seller_name = "未知賣家"
            if "shopee" in url:
                platform = "蝦皮"
                try:
                    # 嘗試抓取蝦皮賣場名稱常用標籤
                    seller_element = driver.find_element(By.CSS_SELECTOR, 'div.V67tSj, span.official-shop-label__name, ._23_19X')
                    seller_name = seller_element.text
                except:
                    seller_name = "需手動檢查(被阻擋)"
            else:
                platform = "Yahoo拍賣"
                try:
                    seller_element = driver.find_element(By.CSS_SELECTOR, '.yui3-u-1 .name, .seller-name')
                    seller_name = seller_element.text
                except:
                    seller_name = "需手動檢查"

            # --- 售價解析 ---
            price = "價格未定"
            try:
                # 尋找包含 $ 符號或數字的價格區塊
                price_match = re.search(r'\$\s*[0-9,]+', page_source)
                if price_match:
                    price = price_match.group()
            except:
                pass

            # --- 適用樂器 (關鍵字掃描) ---
            instrument = "不限/未知"
            content_lower = page_source.lower()
            if any(k in content_lower for k in ["alto", "中音"]):
                instrument = "中音Alto"
            elif any(k in content_lower for k in ["tenor", "次中音"]):
                instrument = "次中音Tenor"
            elif any(k in content_lower for k in ["soprano", "高音"]):
                instrument = "高音Soprano"

            all_data.append({
                "來源平台": platform,
                "賣方名稱": seller_name,
                "適用樂器": instrument,
                "售價": price,
                "商品網址": url
            })
        except Exception as e:
            st.error(f"網址解析失敗: {url}")
        
        progress_bar.progress((index + 1) / len(urls))
    
    driver.quit()
    return pd.DataFrame(all_data)

# --- Streamlit UI ---
st.title("🎷 薩克斯風吹嘴市場調查系統 (雲端修復版)")

# 網址輸入區域
with st.form("url_input_form", clear_on_submit=True):
    new_url = st.text_input("請輸入蝦皮或 Yahoo 商品網址：")
    submitted = st.form_submit_button("新增調查網址")
    if submitted and new_url:
        if new_url not in st.session_state.url_list:
            st.session_state.url_list.append(new_url)
            st.success("網址已成功加入清單！")

# 顯示與操作
if st.session_state.url_list:
    st.write(f"目前監控中數量：{len(st.session_state.url_list)}")
    with st.expander("查看所有網址"):
        for u in st.session_state.url_list:
            st.text(u)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 開始爬取"):
            df = scrape_data(st.session_state.url_list)
            if not df.empty:
                st.session_state.results = df
                st.dataframe(df)
    
    with col2:
        if st.button("🧹 清空網址"):
            st.session_state.url_list = []
            st.rerun()

    # 下載區域
    if 'results' in st.session_state:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.results.to_excel(writer, index=False)
        st.download_button(
            label="📥 下載 Excel 報表",
            data=output.getvalue(),
            file_name="sax_mouthpiece_survey.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
