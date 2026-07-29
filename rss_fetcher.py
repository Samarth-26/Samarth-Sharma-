from dataclasses import dataclass
from typing import List, Dict

import feedparser
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

from config import RSS_FEEDS, ARTICLES_PER_FEED


@dataclass
class FeedItem:
    
    url: str
    channel_name: str   # the human-readable name from config.py, e.g. "NDTV"
    feed_title: str      # the headline as given in the RSS feed
    feed_published: str  # raw published string from the feed, if present


def fetch_recent_urls(feeds: Dict[str, str] = RSS_FEEDS,
                       per_feed: int = ARTICLES_PER_FEED) -> List[FeedItem]:
    
    all_items: List[FeedItem] = []

    for channel_name, feed_url in feeds.items():
        print(f"[INFO] Fetching RSS feed for: {channel_name} ({feed_url})")
        try:
            # Pass agent header here so news sites don't block the request
            parsed = feedparser.parse(feed_url, agent=USER_AGENT)

            if parsed.bozo and not parsed.entries:
                
                print(f"[WARN] Could not parse feed for {channel_name}. Skipping.")
                continue

            if not parsed.entries:
                print(f"[WARN] Feed for {channel_name} returned no entries. Skipping.")
                continue

            for entry in parsed.entries[:per_feed]:
                link = getattr(entry, "link", None)
                if not link:
                    continue

                all_items.append(
                    FeedItem(
                        url=link,
                        channel_name=channel_name,
                        feed_title=getattr(entry, "title", "Untitled"),
                        feed_published=getattr(entry, "published", "Unknown"),
                    )
                )

        except Exception as e:
            print(f"[ERROR] Failed to fetch/parse feed for {channel_name}: {e}")
            continue

    return all_items


if __name__ == "__main__":
  
    items = fetch_recent_urls()
    print(f"\n[INFO] Pulled {len(items)} recent article links total.\n")
    for item in items:
        print(f"{item.channel_name:16s} | {item.feed_published:30s} | {item.feed_title}")
        print(f"    {item.url}")