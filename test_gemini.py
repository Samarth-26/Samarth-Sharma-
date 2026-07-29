
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL

print(f"[TEST] GEMINI_API_KEY present: {bool(GEMINI_API_KEY)} (length={len(GEMINI_API_KEY)})")
print(f"[TEST] GEMINI_MODEL = {GEMINI_MODEL!r}")

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Say hello in exactly 5 words.",
    )
    print("[TEST] SUCCESS:")
    print(response.text)
except Exception as exc:
    print("[TEST] FAILED with exception:")
    print(repr(exc))