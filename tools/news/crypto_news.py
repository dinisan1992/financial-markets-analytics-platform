from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import requests
import mysql.connector
from mysql.connector import Error
import os

from config import DB_CONFIG

# =========================
# SETTINGS
# =========================
MYSQL_CONFIG = DB_CONFIG

API_TOKEN = os.getenv("CRYPTOPANIC_API_TOKEN", "")
API_URL = "https://cryptopanic.com/api/developer/v2/posts/"


# =========================
# CREATE MYSQL TABLE IF IT DOES NOT EXIST
# =========================
def create_table_if_not_exists(conn):
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS crypto_news (
        news_id INT AUTO_INCREMENT PRIMARY KEY,
        snapped_at DATETIME NOT NULL,
        title VARCHAR(500) NOT NULL,
        description TEXT,
        original_url VARCHAR(1000),
        inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY unique_url (original_url)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    conn.commit()
    cursor.close()

# =========================
# FETCH NEWS FROM THE API
# =========================
def fetch_news():
    if not API_TOKEN:
        print("CRYPTOPANIC_API_TOKEN is not configured in the environment.")
        return []

    try:
        response = requests.get(
            API_URL,
            params={
                "auth_token": API_TOKEN,
                "currencies": "BTC",
                "public": "true",
                "kind": "news",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        news_list = data.get('results', [])
        print(f"✅ News received: {len(news_list)}")
        return news_list
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

# =========================
# FILTER IMPORTANT NEWS
# =========================
def filter_important_news(news_list, min_rank=50, min_positive_votes=5):
    important_news = []
    for news in news_list:
        rank = news.get('rank', 0)
        positive_votes = news.get('positive_votes', 0)
        if rank >= min_rank or positive_votes >= min_positive_votes:
            important_news.append(news)
    print(f"✅ Important news filtered: {len(important_news)}")
    return important_news

# =========================
# SAVE NEWS TO MYSQL
# =========================
def save_news_to_db(news_list, conn):
    cursor = conn.cursor()

    check_sql = "SELECT COUNT(*) FROM crypto_news WHERE original_url = %s"
    insert_sql = """
    INSERT INTO crypto_news (
        snapped_at, title, description, original_url
    ) VALUES (%s, %s, %s, %s)
    """

    inserted_count = 0

    for news in news_list:
        try:
            news_url = f"https://cryptopanic.com/news/{news['id']}"
            cursor.execute(check_sql, (news_url,))
            exists = cursor.fetchone()[0]

            if exists:
                continue  # News item already inserida

            snapped_at = news.get('published_at', '').replace('T', ' ').replace('Z', '')
            title = news.get('title', '')[:500]
            description = news.get('description', None)

            cursor.execute(insert_sql, (
                snapped_at,
                title,
                description,
                news_url
            ))
            inserted_count += 1

        except Exception as e:
            print(f"⚠️ Error inserting news item ID {news.get('id')}: {e}")

    conn.commit()
    cursor.close()
    print(f"✅ {inserted_count} news inserted into the database.")

# =========================
# MAIN FUNCTION
# =========================
def main():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        if conn.is_connected():
            print("🔗 MySQL connection established.")
            create_table_if_not_exists(conn)
            news = fetch_news()
            if news:
                save_news_to_db(news, conn)
            else:
                print("⚠️ No news to process.")
    except Error as e:
        print(f"❌ Connection error MySQL: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("🔌 MySQL connection closed.")

# =========================
# EXECUTION
# =========================
if __name__ == "__main__":
    main()

