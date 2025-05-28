import google.generativeai as genai
from .config import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)

def generate(prompt: str) -> str:
    resp = _model.generate_content(
        prompt,
        generation_config={"temperature":0.3, "max_output_tokens":300}
    )
    return resp.text.strip()
