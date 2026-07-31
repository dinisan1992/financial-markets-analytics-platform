import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pymysql
import requests


PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_CONFIG


API_KEY = os.getenv("NEWSDATA_API_KEY", "")
CATEGORIES = ["business", "politics", "world"]
COUNTRIES = [
    "us", "gb", "ae", "af", "be", "br", "ca", "cn", "cw", "fi",
    "fr", "de", "gh", "va", "hk", "in", "iq", "ir", "il", "jp",
    "kp", "kr", "lu", "pk", "ps", "pt", "ru", "sa", "za", "ch",
    "sy", "tw", "ua", "wo",
]
GROUP_SIZE = 5
DELAY_BETWEEN_GROUPS = 10
DELAY_BETWEEN_RUNS = 3600
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3


def fetch_news(country_group, max_retries=MAX_RETRIES):
    if not API_KEY:
        print("NEWSDATA_API_KEY is not configured in the environment.")
        return []

    params = {
        "apikey": API_KEY,
        "country": ",".join(country_group),
        "category": ",".join(CATEGORIES),
        "language": "en",
        "timezone": "Europe/London",
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                "https://newsdata.io/api/1/latest",
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 429 and attempt < max_retries:
                delay = min(60, 5 * (2 ** (attempt - 1)))
                print(f"Rate limited for {params['country']}; retrying in {delay}s.")
                time.sleep(delay)
                continue

            response.raise_for_status()
            results = response.json().get("results") or []
            return [
                {
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
                    "link": article.get("link"),
                }
                for article in results
            ]
        except requests.RequestException as exc:
            print(f"News request failed for {params['country']} ({attempt}/{max_retries}): {exc}")
            if attempt < max_retries:
                time.sleep(min(30, 2 ** attempt))

    return []


def save_news_batch(cursor, news_data):
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
    for article in news_data:
        cursor.execute(sql, article)


def run_once(group_delay=DELAY_BETWEEN_GROUPS):
    if not API_KEY:
        raise RuntimeError("NEWSDATA_API_KEY is not configured")

    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            for index in range(0, len(COUNTRIES), GROUP_SIZE):
                country_group = COUNTRIES[index:index + GROUP_SIZE]
                news_data = fetch_news(country_group)
                save_news_batch(cursor, news_data)
                connection.commit()
                print(f"Saved {len(news_data)} articles for {country_group}.")
                if group_delay and index + GROUP_SIZE < len(COUNTRIES):
                    time.sleep(group_delay)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main(continuous=False, group_delay=DELAY_BETWEEN_GROUPS, run_delay=DELAY_BETWEEN_RUNS):
    while True:
        print(f"Starting world-news import at {datetime.now():%Y-%m-%d %H:%M:%S}")
        try:
            run_once(group_delay=group_delay)
        except Exception as exc:
            print(f"World-news import failed: {exc}")

        if not continuous:
            return
        time.sleep(run_delay)


def parse_args():
    parser = argparse.ArgumentParser(description="Import world news into the configured database.")
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Repeat the import at the configured interval.",
    )
    parser.add_argument("--group-delay", type=int, default=DELAY_BETWEEN_GROUPS)
    parser.add_argument("--run-delay", type=int, default=DELAY_BETWEEN_RUNS)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    main(
        continuous=arguments.continuous,
        group_delay=max(0, arguments.group_delay),
        run_delay=max(1, arguments.run_delay),
    )
