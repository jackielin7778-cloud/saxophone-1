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

# --- 1. 頁面初始化與環境檢查 ---
st.set_page_config(page_title="🎷 薩克斯風吹嘴市調系統", layout="wide")

if 'url_list' not in st.session_state:
    st.session_state.url_list = []

def get_driver():
    """建立具備隱身特徵的瀏覽器"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 雲端執行必須
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 關鍵：隱藏 Selenium 的自動化特徵
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 隨機 User-Agent 防止被直接識別為機房機器人
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(ua_list)}")
    
    # 偵測 Chromium 路徑
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 執行腳本以移除 webdriver 屬性
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def scrape_engine(urls):
    """核心爬蟲引擎"""
    all_data = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:])) # 只顯示最後 10 條

    log("🚀 瀏覽器啟動中...")
    try:
        driver = get_driver()
        # --- 預熱 Session (防止直接跳轉登入) ---
        log("🛠️ 正在初始化 Session，模擬正常用戶訪問...")
        driver.get("https://www.google.com")
        time.sleep(2)
        driver.get("https://shopee.tw/")
        time.sleep(3)
    except Exception as e:
        log(f"❌ 驅動程式異常: {str(e)}")
        return pd.DataFrame()

    progress_bar = st.progress(0)
    for index, url in enumerate(urls):
        try:
            log(f"🔎 正在抓取 ({index+1}/{len(urls)}): {url[:40]}...")
            
            # 偽裝來源網頁
            driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': {'Referer': 'https://www.google.com/'}})
            driver.get(url)
            
            # 隨機停留，模擬閱讀
            load_time = random.uniform(5, 10)
            log(f"⏳ 等待渲染 {load_time:.1f} 秒...")
            time.sleep(load_time)
            
            # 檢查結果
            title = driver.title
            log(f"📄 網頁標題: {title}")
            
            if "登入" in title or "Login" in title:
                log("⚠️ 遇到登入牆，請嘗試手動輸入具體商品網址。")

            # --- 數據解析邏輯 ---
            platform = "蝦皮" if "shopee" in url else "Yahoo拍賣"
            seller = "未知賣家"
            price = "尚未擷取"
            
            # 1. 抓取賣家
            try:
                if platform == "蝦皮":
                    # 蝦皮賣家多種 CSS 選取器嘗試
                    s_el = driver.find_elements(By.CSS_SELECTOR, 'span.V67tSj, ._23_19X, .official-shop-label__name')
                    seller = s_el[0].text if s_el else "偵測不到賣家"
                else:
                    s_el = driver.find_elements(By.CSS_SELECTOR, '.seller-name, a[data-curst]')
                    seller = s_el[0].text if s_el else "偵測不到賣家"
            except: pass

            # 2. 抓取價格
            try:
                price_match = re.search(r'\$\s*[0-9,]+', driver.page_source)
                price = price_match.group() if price_match else "需進入網頁看"
            except: pass

            # 3. 樂器判定
            content = driver.page_source.lower()
            instrument = "其他/通用"
            if any(k in content for k in ["alto", "中音"]): instrument = "中音Alto"
            elif any(k in content for k in ["tenor", "次中音"]): instrument = "次中音Tenor"
            elif any(k in content for k in ["soprano", "高音"]): instrument = "高音Soprano"

            all_data.append({
                "賣方名稱": seller,
                "適用樂器": instrument,
                "售價": price,
                "來源平台": platform,
                "商品網址": url
            })
            log(f"✅ 完成解析: {seller} | {instrument}")

        except Exception as e:
            log(f"❌ 單筆解析錯誤: {str(e)}")
        
        progress_bar.progress((index + 1) / len(urls))

    driver.quit()
    log("🏁 調查任務結束，瀏覽器已安全關閉。")
    return pd.DataFrame(all_data)

# --- 2. 前台介面設計 ---
st.title("🎷 薩克斯風吹嘴市場調查工具")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 網址管理")
    url_input = st.text_area("請輸入吹嘴商品網址（每行一個）：", placeholder="https://shopee.tw/product/...", height=150)
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ 更新待爬清單"):
            new_urls = [u.strip() for u in url_input.split("\n") if u.strip()]
            for u in new_urls:
                if u not in st.session_state.url_list:
                    st.session_state.url_list.append(u)
            st.rerun()
    with col_btn2:
        if st.button("🗑️ 清空所有清單"):
            st.session_state.url_list = []
            if 'df_results' in st.session_state: del st.session_state.df_results
            st.rerun()

    if st.session_state.url_list:
        st.info(f"目前清單中共有 {len(st.session_state.url_list)} 個對象")
        with st.expander("查看清單細節"):
            st.write(st.session_state.url_list)

with col2:
    st.subheader("📋 運作狀態 (Logs)")
    # 執行爬蟲
    if st.session_state.url_list:
        if st.button("🚀 開始全數拔回"):
            final_df = scrape_engine(st.session_state.url_list)
            if not final_df.empty:
                st.session_state.df_results = final_df

# --- 3. 結果展示與下載 ---
if 'df_results' in st.session_state:
    st.markdown("---")
    st.subheader("📊 調查結果預覽")
    st.dataframe(st.session_state.df_results, use_container_width=True)
    
    # Excel 下載
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.df_results.to_excel(writer, index=False, sheet_name='Sax_Survey')
    
    st.download_button(
        label="📥 下載 Excel 調查報告",
        data=output.getvalue(),
        file_name=f"sax_survey_{datetime.now().strftime('%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")
st.caption("調查員提示：若蝦皮頻繁出現登入要求，請嘗試減少同時爬取的網址數量，或延長等待時間。")
