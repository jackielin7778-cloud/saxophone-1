import streamlit as st
import pandas as pd
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO

# --- 初始化設定 ---
st.set_page_config(page_title="薩克斯風吹嘴市場調查工具", layout="wide")

# 初始化 session_state 用於儲存追蹤網址，確保重新整理時不會遺失
if 'url_list' not in st.session_state:
    st.session_state.url_list = []

# --- 爬蟲邏輯函數 ---
def scrape_data(urls):
    all_data = []
    
    # 設定 Chrome 選項以避開反爬蟲
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 無頭模式，不彈出視窗
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 模擬真人 User-Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    progress_bar = st.progress(0)
    for index, url in enumerate(urls):
        try:
            driver.get(url)
            # 隨機延遲，避免被判定為機器人
            time.sleep(random.uniform(3, 7)) 
            
            # 邏輯判斷：根據網址區分平台
            platform = "未知"
            if "shopee.tw" in url:
                platform = "蝦皮"
                # 這裡需要根據蝦皮實際的 CSS Selector 進行動態調整
                # 注意：電商平台常更換 Class Name，實務上需定期維護
                name = driver.find_element(By.CSS_SELECTOR, 'span[class*="seller-name"]').text if "shopee" in url else "未知"
                price = driver.find_element(By.CSS_SELECTOR, 'div[class*="price"]').text
            elif "yahoo.com" in url:
                platform = "Yahoo拍賣"
                name = driver.find_element(By.CSS_SELECTOR, 'a[class*="seller-name"]').text
                price = driver.find_element(By.CSS_SELECTOR, 'span[class*="price"]').text
            else:
                name, price = "不支援平台", "0"

            # 判斷適用樂器 (簡單關鍵字邏輯)
            page_content = driver.page_source.lower()
            instrument = "其他"
            if "alto" in page_content or "中音" in page_content:
                instrument = "中音Alto"
            elif "tenor" in page_content or "次中音" in page_content:
                instrument = "次中音Tenor"
            elif "soprano" in page_content or "高音" in page_content:
                instrument = "高音Soprano"

            all_data.append({
                "來源平台": platform,
                "賣方名稱": name,
                "適用樂器": instrument,
                "售價": price,
                "網址連結": url
            })
        except Exception as e:
            st.warning(f"無法擷取網址 {url}: {str(e)}")
        
        progress_bar.progress((index + 1) / len(urls))
    
    driver.quit()
    return pd.DataFrame(all_data)

# --- Streamlit 前台介面 ---
st.title("🎷 薩克斯風吹嘴市場調查系統")
st.markdown("輸入蝦皮或 Yahoo 拍賣的商品網址，系統將自動抓取賣家與規格資訊。")

# 1. 新增調查網址 (不移除舊有紀錄)
with st.container():
    col1, col2 = st.columns([4, 1])
    with col1:
        new_url = st.text_input("輸入新的商品網址：", placeholder="https://shopee.tw/...")
    with col2:
        if st.button("新增網址"):
            if new_url and new_url not in st.session_state.url_list:
                st.session_state.url_list.append(new_url)
                st.success("已加入追蹤清單")
            elif new_url in st.session_state.url_list:
                st.warning("此網址已存在")

# 顯示目前清單
if st.session_state.url_list:
    st.subheader("目前監控中的網址")
    for i, url in enumerate(st.session_state.url_list):
        st.write(f"{i+1}. {url}")
    
    if st.button("🗑️ 清空所有清單"):
        st.session_state.url_list = []
        st.rerun()

    # 2. & 3. 執行爬蟲並產出 Excel
    if st.button("🚀 開始爬取數據"):
        with st.spinner("正在穿越反爬蟲迷霧，請稍候..."):
            df_result = scrape_data(st.session_state.url_list)
            
            if not df_result.empty:
                st.subheader("📊 調查結果預覽")
                st.dataframe(df_result)

                # 轉換為 Excel 格式供下載
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_result.to_excel(writer, index=False, sheet_name='吹嘴調查報告')
                
                st.download_button(
                    label="📥 下載 Excel 報表",
                    data=output.getvalue(),
                    file_name="saxophone_mouthpiece_survey.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("未能成功抓取任何數據。")