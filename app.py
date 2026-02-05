# 1. 安裝必要套件 (Colab 環境專用)
!pip install selenium pandas xlsxwriter
!apt-get update
!apt-get install -y chromium-chromedriver

import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# 2. 設定瀏覽器
def get_colab_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# 3. 執行爬取
def scrape_yahoo_store(store_url):
    target_url = store_url.split('?')[0].rstrip('/') + "/search/auction/product?p=吹嘴"
    driver = get_colab_driver()
    print(f"🚀 正在透過 Google 伺服器潛入: {target_url}")
    
    driver.get(target_url)
    time.sleep(15) # 給予充足加載時間
    
    # 滾動
    driver.execute_script("window.scrollTo(0, 2000);")
    time.sleep(3)

    items = driver.find_elements(By.CSS_SELECTOR, 'li[data-item-id], [class*="Item__itemContainer"], [class*="BaseItem"]')
    print(f"📦 偵測到 {len(items)} 個區塊，開始提取...")

    all_data = []
    brand_list = ["Selmer", "Vandoren", "Yanagisawa", "Meyer", "Yamaha", "Otto Link", "Beechler", "JodyJazz"]

    for el in items:
        try:
            txt = el.text.replace("\n", " ")
            if "$" in txt:
                p_match = re.search(r'\$\s*[0-9,]+', txt)
                price = p_match.group() if p_match else "N/A"
                title = txt.split("$")[0].strip()[:60]
                
                brand = "其他"
                for b in brand_list:
                    if b.lower() in title.lower():
                        brand = b
                        break
                
                all_data.append({"品牌": brand, "商品資訊": title, "售價": price})
        except: continue

    driver.quit()
    df = pd.DataFrame(all_data).drop_duplicates()
    return df

# --- 執行處 ---
url = "https://tw.bid.yahoo.com/booth/Y9133606367" # 你可以換成任何店家
result_df = scrape_yahoo_store(url)

if not result_df.empty:
    print("✅ 成功拔回數據！")
    display(result_df)
    result_df.to_excel("sax_report.xlsx", index=False)
    print("📁 Excel 已存檔，請點選左側資料夾圖示下載。")
else:
    print("❌ Google IP 也被擋了，請嘗試更換 Colab 的運行階段（重新連線）。")
