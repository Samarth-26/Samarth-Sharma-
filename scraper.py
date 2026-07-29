import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dateutil import parser as date_parser
import feedparser
from newspaper import Article
from config import RSS_FEEDS, ARTICLES_PER_FEED

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def parse_exact_datetime(raw_date_str, article_date):
    
    if article_date:
        return article_date.strftime("%Y-%m-%d %H:%M:%S")
    if raw_date_str and raw_date_str != "Unknown":
        try:
            parsed_dt = date_parser.parse(raw_date_str)
            return parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def scrape_single_article(entry, channel_name):
    link = getattr(entry, "link", None)
    if not link:
        return None

    raw_published = getattr(entry, "published", None)

    try:
        article = Article(link, browser_user_agent=USER_AGENT)
        article.download()
        article.parse()
        full_text = article.text if len(article.text) > 100 else entry.get("summary", "")
        title = article.title or getattr(entry, "title", "Untitled")
        exact_datetime = parse_exact_datetime(raw_published, article.publish_date)
        print(f"  [OK] Downloaded: {title[:50]}...")
    except Exception as e:
        # Fallback to RSS snippet if 403 Forbidden or scraping is blocked
        print(f"  [WARN] Scrape fallback for {channel_name} link ({e}). Using RSS summary.")
        title = getattr(entry, "title", "Untitled")
        full_text = f"{title}. {entry.get('summary', '')}"
        exact_datetime = parse_exact_datetime(raw_published, None)

    return {
        "channel": channel_name,
        "title": title,
        "url": link,
        "exact_datetime": exact_datetime,
        "full_text": full_text
    }

def scrape_full_news_articles():
    
    scraped_articles = []
    tasks = []

    print("[INFO] Initiating multi-threaded article scraping...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        for channel_name, feed_url in RSS_FEEDS.items():
            print(f"[INFO] Fetching RSS feed: {channel_name}...")
            feed = feedparser.parse(feed_url, agent=USER_AGENT)
            entries = feed.entries[:ARTICLES_PER_FEED]
            for entry in entries:
                tasks.append(executor.submit(scrape_single_article, entry, channel_name))

        for future in tasks:
            res = future.result()
            if res:
                scraped_articles.append(res)

    print(f"\n[SUCCESS] Total articles ready for NLP engine: {len(scraped_articles)}")
    return scraped_articles