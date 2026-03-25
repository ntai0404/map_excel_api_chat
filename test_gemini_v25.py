import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_KEYS").split(",")[0].strip()
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
model = "gemini-2.0-flash"  # Testing stable 2026 model

print(f"Testing Gemini model: {model}")
client = OpenAI(api_key=key, base_url=base_url)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello!"}],
        max_tokens=10
    )
    print("SUCCESS:", response.choices[0].message.content)
except Exception as e:
    print("FAILED:", e)
