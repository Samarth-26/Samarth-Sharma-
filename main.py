
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import FLASK_PORT
from app import create_app

if __name__ == "__main__":
    print("=" * 62)
    print("  NLP News Entity Pipeline — Live Web Dashboard")
    print("=" * 62)
    print(f"  Server  : http://localhost:{FLASK_PORT}")
    print(f"  Feeds   : 5 Indian news portals")
    print(f"  NLP     : spaCy en_core_web_sm  +  keyword heuristics")
    print(f"  Chatbot : Gemini 1.5 Flash (set GEMINI_API_KEY in config.py)")
    print("=" * 62)

    application = create_app()
    application.run(
        host="0.0.0.0",
        port=FLASK_PORT,
        debug=False,
        threaded=True,
        use_reloader=False,
    )