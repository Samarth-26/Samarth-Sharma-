import os
import csv
from datetime import datetime, timedelta
 
CSV_FIELDS = ["channel", "title", "url", "exact_datetime", "full_text"]
 
 
def save_articles_to_csv(articles, path):
    """Writes scraped articles to CSV, overwriting any previous cache."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for article in articles:
            writer.writerow({field: article.get(field, "") for field in CSV_FIELDS})
    print(f"[CACHE] Saved {len(articles)} articles to {path}")
 
 
def load_articles_from_csv(path):
    """Reads back the CSV into the same list-of-dicts shape scraper.py produces."""
    if not os.path.exists(path):
        return []
    articles = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            articles.append(dict(row))
    return articles
 
 
def is_cache_fresh(path, max_age_minutes):
    """True if the CSV exists and was written within the last max_age_minutes."""
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime < timedelta(minutes=max_age_minutes)
 
 
def cache_age_minutes(path):
    """How old the cache file is, in minutes. Returns None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return (datetime.now() - mtime).total_seconds() / 60
 