import re
import spacy
from transformers import pipeline
from config import SPACY_MODEL, ZERO_SHOT_MODEL, PRIMARY_CATEGORIES, SPORTS_LIST, POLITICAL_PARTIES


print("[INIT] Loading spaCy model...")
nlp = spacy.load(SPACY_MODEL)

print("[INIT] Loading Hugging Face zero-shot classifier...")
classifier = pipeline("zero-shot-classification", model=ZERO_SHOT_MODEL)

CLASSIFICATION_CACHE = {}

def build_entity_context(entity_name, article_text, window=300):
    
    idx = article_text.find(entity_name)
    if idx == -1:
        # Try a looser match (handles trailing 's / possessive forms, etc.)
        idx = article_text.lower().find(entity_name.lower().rstrip("'s").rstrip("’s"))

    if idx == -1:
        snippet = article_text[:window]
    else:
        start = max(0, idx - window // 2)
        end = min(len(article_text), idx + len(entity_name) + window // 2)
        snippet = article_text[start:end]

    return snippet.strip()

def classify_entity_cached(entity_name, article_text, candidate_labels):
    
    context = build_entity_context(entity_name, article_text)
    key = (entity_name.lower().strip(), context.lower().strip(), tuple(candidate_labels))
    if key in CLASSIFICATION_CACHE:
        return CLASSIFICATION_CACHE[key]

   
    classification_input = f"{entity_name}. {context}" if context else entity_name
    result = classifier(classification_input, candidate_labels=candidate_labels)
    top_label = result['labels'][0]
    CLASSIFICATION_CACHE[key] = top_label
    return top_label

def extract_political_party(text):
    """Extracts exact political party using regex matching."""
    for party_name, pattern in POLITICAL_PARTIES:
        if re.search(pattern, text, re.IGNORECASE):
            return party_name
    return "Government & Politics"

def extract_published_book(doc, text):
    """Extracts book titles from WORK_OF_ART entities or context."""
    for ent in doc.ents:
        if ent.label_ in ["WORK_OF_ART", "LAW"]:
            return f"'{ent.text.strip()}'"
    match = re.search(r'author of ["\']([^"\']+)["\']|book titled ["\']([^"\']+)["\']', text, re.IGNORECASE)
    if match:
        title = match.group(1) or match.group(2)
        return f"'{title}'"
    return "Recent Publication / Article"

def extract_specific_details(entity_name, category, article_text, doc):
    """Generates granular contextual sub-details based on category."""
    if category == "Sportsperson":
        res = classifier(article_text[:1000], candidate_labels=SPORTS_LIST)
        top_sport = res['labels'][0]
        return f"Sportsperson ({top_sport})"

    elif category == "Politician":
        party = extract_political_party(article_text)
        return f"Politician ({party})"

    elif category == "Author":
        book = extract_published_book(doc, article_text)
        return f"Author (Book: {book})"

    elif category == "Actor / Entertainer":
        return "Actor / Cinema & Media"

    elif category == "Businessman":
        return "Businessman / Industry Leader"

    elif category == "Government Official":
        return "Government Official / Institution"

    return category

def process_article_entities(article_data):
    
    text = article_data["full_text"]
    if not text:
        return []

    doc = nlp(text[:3000])
    processed_entities = []
    seen = set()

    for ent in doc.ents:
        clean_name = ent.text.strip()

        # Strict Filter: Only process Proper Nouns of People (PERSON) with at least 2 words
        if ent.label_ == "PERSON" and len(clean_name.split()) >= 2:
            key = clean_name.lower()
            if key in seen:
                continue
            seen.add(key)

            primary_cat = classify_entity_cached(clean_name, text, PRIMARY_CATEGORIES)
            specific_detail = extract_specific_details(clean_name, primary_cat, text, doc)

            processed_entities.append({
                "name": clean_name,
                "category": primary_cat,
                "specific_detail": specific_detail,
                "channel": article_data["channel"],
                "exact_datetime": article_data["exact_datetime"],
                "article_title": article_data["title"],
                "article_url": article_data["url"]
            })

    return processed_entities