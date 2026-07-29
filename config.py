from dotenv import load_dotenv
load_dotenv()
RSS_FEEDS = {
    "Times of India": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "The Hindu": "https://www.thehindu.com/feeder/default.rss",
    "NDTV": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "India Today": "https://www.indiatoday.in/rss/home",
    "Indian Express": "https://indianexpress.com/feed/"
}
 
ARTICLES_PER_FEED = 10
FLASK_PORT = 5000
 
SPACY_MODEL = "en_core_web_sm"
ZERO_SHOT_MODEL = "facebook/bart-large-mnli"
 
PRIMARY_CATEGORIES = [
    "Sportsperson",
    "Politician",
    "Author",
    "Actor / Entertainer",
    "Businessman",
    "Government Official"
]
 
SPORTS_LIST = [
    "Cricket", "Football", "Tennis", "Badminton", "Basketball",
    "Hockey", "Chess", "Athletics", "Motorsport", "Golf"
]
 
POLITICAL_PARTIES = [
    ("BJP", r"\b(BJP|Bharatiya Janata Party)\b"),
    ("Congress", r"\b(Congress|INC|Indian National Congress)\b"),
    ("AAP", r"\b(AAP|Aam Aadmi Party)\b"),
    ("TMC", r"\b(TMC|Trinamool|Trinamool Congress)\b"),
    ("DMK", r"\b(DMK|Dravida Munnetra Kazhagam)\b"),
    ("SP", r"\b(Samajwadi Party|SP)\b"),
    ("BSP", r"\b(Bahujan Samaj Party|BSP)\b"),
    ("Democratic Party", r"\b(Democrats?|Democratic Party)\b"),
    ("Republican Party", r"\b(Republicans?|GOP|Republican Party)\b"),
]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
FETCH_INTERVAL_SECONDS = 300  # 5 minutes — matches "Auto-refreshes every 5 min" in the dashboard UI
OUTPUT_HTML_PATH = "output/index.html"
TEMPLATE_DIR = "templates"
TEMPLATE_NAME = "report_template.html"
 

import os
 
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL     = "openai/gpt-oss-20b"
 
if GROQ_API_KEY:
    print(f"[CONFIG] GROQ_API_KEY loaded: {GROQ_API_KEY[:8]}... (len={len(GROQ_API_KEY)})")
else:
    print("[CONFIG] GROQ_API_KEY is EMPTY — check that .env exists and is named exactly '.env'")
 
# Legacy Gemini config (kept for reference)
GEMINI_MODEL   = "gemini-2.0-flash-lite"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
 

HISTORY_PATH = "data/history.json"
PIPELINE_HEALTH_PATH = "data/pipeline_health.json"
HISTORY_MAX_RUNS = 30
ALERT_Z_SCORE_THRESHOLD = 2.0
EXECUTIVE_BRIEF_MODEL = GROQ_MODEL
PDF_EXPORT_PATH = "output/executive_daily_brief.pdf"
CSV_PATH = "data/articles.csv"
CSV_COLUMNS = ["channel", "title", "url", "exact_datetime", "full_text"]
SPORT_KEYWORDS = {
    
    "Cricket":    ["cricket", "wicket", "batsman", "bowler", "century", "ipl", "bcci",
                   "test match", "odi", "t20", "run chase", "innings", "over", "over rate"],
    "Football":   ["football", "soccer", "goal", "striker", "midfielder", "defender",
                   "fifa", "isl", "premier league", "la liga", "serie a", "penalty kick"],
    "Tennis":     ["tennis", "grand slam", "wimbledon", "atp", "wta", "us open",
                   "australian open", "french open", "deuce", "ace serve"],
    "Badminton":  ["badminton", "shuttlecock", "bwf", "smash shuttle"],
    "Basketball": ["basketball", "nba", "three-pointer", "slam dunk", "nba finals"],
    "Hockey":     ["field hockey", "fih", "hockey india", "hockey world cup"],
    "Chess":      ["chess", "grandmaster", "fide", "checkmate", "chess olympiad"],
    "Athletics":  ["100m sprint", "400m run", "long jump", "high jump", "shot put",
                   "discus throw", "javelin", "pole vault", "decathlon", "hurdles race",
                   "world athletics", "track and field"],
    "CWG":        ["commonwealth games", "cwg 2026", "cwg medal", "glasgow cwg"],
    "Olympics":   ["olympic games", "olympic medal", "olympic gold", "olympic silver",
                   "olympic bronze", "paris olympics", "olympic village"],
    "Motorsport": ["formula 1", "f1 race", "motogp", "grand prix", "pit stop", "lap time"],
    "Golf":       ["golf", "pga tour", "birdie", "bogey", "par golf", "golf course"],
    "Wrestling":  ["wrestler", "wrestling", "wwe", "akhada", "kushti", "bout wrestling"],
    "Boxing":     ["boxing", "knockout", "bout", "heavyweight", "welterweight", "jab cross"],
}
 
ACTOR_KEYWORDS = [
    "actor", "actress", "film", "movie", "bollywood", "box office",
    "director", "trailer", "cinema", "ott", "web series", "casting",
    "blockbuster", "debut film", "co-star", "screenplay",
]
 
MOVIE_PATTERNS = [
    r'film ["\']([^"\']+)["\']',
    r'movie ["\']([^"\']+)["\']',
    r'starrer ["\']([^"\']+)["\']',
]