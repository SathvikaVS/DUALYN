"""
The only file in the project that talks to Gemini directly.
If the AI provider ever changes, only this file should need editing -
skill_analyzer.py and everything upstream of it stays the same (Section 28:
"keep the AI layer replaceable").
"""
import os
from google import genai

_client = None


def get_client():
    """
    Lazily creates the Gemini client so importing this module never fails
    just because GEMINI_API_KEY isn't set yet (e.g. during tests or before
    the .env is configured).
    """
    global _client
    if _client is None:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate_text(prompt, model='gemini-2.0-flash'):
    """
    Sends one prompt to Gemini and returns the raw text response.
    Raises on failure - callers decide how to handle that (Section 27:
    "AI/API failure" is a named error case, not something to hide here).
    """
    client = get_client()
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text