from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import requests
import time
import pymysql
import os
from datetime import datetime

from config import DB_CONFIG

# ------------------------
# CONFIGURATION
# ------------------------
API_KEY = os.getenv("NEWSDATA_API_KEY", "")

CATEGORIES = ["business", "politics", "world"]
COUNTRIES = [
    "us", "gb", "ae", "af", "be", "br", "ca", "cn", "cw", "fi",
    "fr", "de", "gh", "va", "hk", "in", "iq", "ir", "il", "jp",
    "kp", "kr", "lu", "pk", "ps", "pt", "ru", "sa", "za", "ch",
    "sy", "tw", "ua", "wo"
]
GROUP_SIZE = 5
DELAY_BETWEEN_GROUPS = 10  # segundos
DELAY_BETWEEN_RUNS = 3600  # 1 hora em segundos

# ------------------------
# FUNCTION TO FETCH NEWS
# ------------------------
def fetch_news(country_group):
    if not API_KEY:
        print("NEWSDATA_API_KEY not configurada no .env.")
        return []

    countries_str = ",".join(country_group)
    url = (
        f"https://newsdata.io/api/1/latest?"
        f"apikey={API_KEY}&"
        f"country={countries_str}&"
        f"category={','.join(CATEGORIES)}&"
        f"language=en&timezone=Europe/London"
    )

    print(f"🔎 Fetching news for: {country_group}")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 429:
            print(f"⚠️ 429 Too Many Requests for {countries_str}, waiting 15s...")
            time.sleep(15)
            return fetch_news(country_group)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            print(f"⚠️ No news returned for {country_group}")
            return []

        news_list = []
        for article in data["results"]:
            news_list.append({
                "article_id": article.get("article_id"),
                "snapped_at": article.get("pubDate"),
                "title": article.get("title"),
                "description": article.get("description"),
                "content": article.get("content"),
                "original_url": article.get("link"),
                "source_name": article.get("source_id"),
                "source_url": article.get("source_url"),
                "country": article.get("country"),
                "category": article.get("category"),
                "language": article.get("language"),
                "inserted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "link": article.get("link")
            })
        return news_list

    except Exception as e:
        print(f"❌ Error para {countries_str}: {e}")
        return []

# ------------------------
# MAIN HOURLY LOOP
# ------------------------
while True:
    print(f"\n🕒 Starting execution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        # Connection MYSQL
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("🔗 MySQL connection established.")

        # Process countries in groups
        for i in range(0, len(COUNTRIES), GROUP_SIZE):
            country_group = COUNTRIES[i:i + GROUP_SIZE]
            news_data = fetch_news(country_group)
            print(f"✅ {len(news_data)} news coletadas para {country_group}")

            for article in news_data:
                try:
                    sql = """
                        INSERT INTO world_news 
                        (article_id, snapped_at, title, description, content, original_url, 
                         source_name, source_url, country, category, language, inserted_at, link)
                        VALUES (%(article_id)s, %(snapped_at)s, %(title)s, %(description)s, %(content)s, 
                                %(original_url)s, %(source_name)s, %(source_url)s, %(country)s, 
                                %(category)s, %(language)s, %(inserted_at)s, %(link)s)
                        ON DUPLICATE KEY UPDATE 
                            title = %(title)s,
                            description = %(description)s,
                            content = %(content)s,
                            inserted_at = %(inserted_at)s
                    """
                    cursor.execute(sql, article)
                except Exception as e:
                    print(f"❌ Error inserting no DB: {e}")

            conn.commit()
            print(f"💾 Group {i//GROUP_SIZE + 1} inserted into the database successfully.")
            time.sleep(DELAY_BETWEEN_GROUPS)

        cursor.close()
        conn.close()
        print("📌 Execution complete. Waiting for the next hour...")

    except Exception as e:
        print(f"❌ General error during execution: {e}")

    # Wait 1 hour for the next execution
    time.sleep(DELAY_BETWEEN_RUNS)

