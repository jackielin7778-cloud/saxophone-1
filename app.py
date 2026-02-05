import streamlit as st
import pandas as pd
import time
import random
import re
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from io import BytesIO

# --- 頁面配置 ---
st.set_page_config(page_title="🎷 薩克斯風吹嘴搜尋全數拔回", layout="wide")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            chrome_options.binary_location = path
            break
            
    service = Service("/usr/bin/chromedriver") if os.path.exists("/usr/bin/chromedriver") else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def identify_brand(title):
    brands = {
        "Selmer": ["selmer", "塞爾瑪", "s80", "s90"],
        "Vandoren": ["vandoren", "凡多倫", "萬多林"],
        "Yanagisawa": ["yanagisawa", "柳澤"],
        "Meyer": ["meyer"],
        "Yamaha": ["yamaha", "山葉"],
        "JodyJazz": ["jodyjazz", "jody jazz"],
        "Otto Link": ["otto link", "ottolink"],
        "D'Addario": ["d'addario", "daddario"]
    }
    t_lower = title.lower()
    for brand, keywords in brands.items():
        if any(k in t_lower for k in keywords):
            return brand
    return "其他/自製"

def scrape_search_page(url):
    all_items = []
    log_placeholder = st.empty()
    logs = []

    def log(msg):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_placeholder.code("\n".join(logs[-10:]))

    try:
        driver = get_driver()
        log("🚀 執行終極解析方案...")
        driver.get(url)
        time.sleep(8) # 給予充足時間加載 JavaScript
        
        # --- 核心邏輯：從原始碼提取 JSON 數據 ---
        log("🔍 正在掃描網頁後台數據區塊...")
        page_source = driver.page_source
        
        # Yahoo 拍賣的商品數據通常存在於網頁中的 JSON 格式
        # 我們直接用正則表達式抓取包含價格與標題的字串
        # 尋找模式：{"title":"...","price":"..."}
        found_data = re.findall(r'{"title":"([^"]+)","ecPrice":"(\d+)"[^}]+"sellerName":"([^"]+)"', page_source)
        
        if not found_data:
            log("⚠️ JSON 提取失敗，切換至 DOM 樹遍歷模式...")
            # 嘗試抓取所有具有商品特徵的節點
            items = driver.find_elements(By.XPATH, "//a[contains(@class, 'ItemName')] | //span[contains(@class, 'ItemName')]")
            log(f"📦 找到 {len(items)} 個潛在連結標籤")
            
            for item in items:
                try:
                    title = item.text
                    if len(title) < 5: continue
                    # 尋找該標籤附近的價格
                    parent = item.find_element(By.XPATH, "./ancestor::div[10]")
                    price_text = parent.text
                    price_match = re.search(r'\$\s*[0-9,]+', price_text)
                    price = price_match.group() if price_match else "N/A"
                    
                    all_items.append({
                        "品牌": identify_brand(title),
                        "賣方名稱": "搜尋結果賣家",
                        "商品資訊": title,
                        "適用樂器": "中音/次中音" if "alto" in title.lower() or "中音" in title.lower() else "其他",
                        "售價": price
                    })
                except: continue
        else:
            for title, price, seller in found_data:
                # 品牌與樂器判定
                brand = identify_brand(title)
                t_lower = title.lower()
                instrument = "其他"
                if "alto" in t_lower or "中音" in t_lower: instrument = "中音Alto"
                elif "tenor" in t_lower or "次中音" in t_lower: instrument = "次中音Tenor"
                elif "soprano" in t_lower or "高音" in t_lower: instrument = "高音Soprano"
                
                all_items.append({
                    "品牌": brand,
                    "賣方名稱": seller,
                    "商品資訊": title,
                    "適用樂器": instrument,
                    "售價": f"${price}"
                })

        df = pd.DataFrame(all_items).drop_duplicates(subset=['商品資訊'])
        log(f"✅ 成功拔回 {len(df)} 筆數據")
        driver.quit()
        return df

    except Exception as e:
        log(f"❌ 異常: {str(e)}")
        return pd.DataFrame()

# UI 介面與之前相同
st.title("🎷 薩克斯風吹嘴市調系統 (終極解析版)")
url_input = st.text_input("輸入 Yahoo 搜尋結果網址：")
if st.button("🚀 執行全頁拔回"):
    if url_input:
        res = scrape_search_page(url_input)
        if not res.empty:
            st.session_state.final_res = res
            st.dataframe(res)
        else:
            st.error("連終極方案也抓不到數據。這極可能是因為雲端 IP 被 Yahoo 徹底屏蔽。")

if 'final_res' in st.session_state:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.final_res.to_excel(writer, index=False)
    st.download_button("📥 下載 Excel 報告", output.getvalue(), "sax_report.xlsx")
