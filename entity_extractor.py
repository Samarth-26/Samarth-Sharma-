from dataclasses import dataclass
from typing import List
 
import spacy
 
from config import SPACY_MODEL, ENTITY_TYPES_OF_INTEREST
from scraper import ScrapedArticle
 
# Load the spaCy model once at module import time (expensive to reload).
try:
    _nlp = spacy.load(SPACY_MODEL)
except OSError:
    raise OSError(
        f"spaCy model '{SPACY_MODEL}' not found. "
        f"Install it with: python -m spacy download {SPACY_MODEL}"
    )
 
 
@dataclass
class ExtractedEntity:
   
    text: str          # e.g. "Lionel Messi"
    label: str         # e.g. "PERSON" or "ORG"
    source: str        # news source domain
    article_date: str  # publish date string
    article_title: str
 
 
def extract_entities(article: ScrapedArticle) -> List[ExtractedEntity]:
    
  
    text = article.text[: _nlp.max_length]
    doc = _nlp(text)
 
    seen = set()
    entities: List[ExtractedEntity] = []
 
    for ent in doc.ents:
        if ent.label_ not in ENTITY_TYPES_OF_INTEREST:
            continue
 
        clean_text = ent.text.strip()
        if not clean_text or len(clean_text) < 2:
            continue
 
        
        key = (clean_text.lower(), ent.label_)
        if key in seen:
            continue
        seen.add(key)
 
        entities.append(
            ExtractedEntity(
                text=clean_text,
                label=ent.label_,
                source=article.source,
                article_date=article.publish_date,
                article_title=article.title,
            )
        )
 
    return entities
 
 
def extract_all(articles: List[ScrapedArticle]) -> List[ExtractedEntity]:
   
    all_entities: List[ExtractedEntity] = []
    for article in articles:
        print(f"[INFO] Extracting entities from: {article.title}")
        all_entities.extend(extract_entities(article))
    return all_entities
 
 
if __name__ == "__main__":
    # Quick manual test
    from rss_fetcher import fetch_recent_urls
    from scraper import scrape_all
 
    items = fetch_recent_urls()
    urls = [item.url for item in items]
    overrides = {item.url: item.channel_name for item in items}
    scraped = scrape_all(urls, source_overrides=overrides)
    entities = extract_all(scraped)
    for e in entities:
        print(f"{e.label:8s} | {e.text:30s} | {e.source}")