"""
Small, reusable helper around the OpenAI Chat Completions API.

Why have this?
- So every service can call LLMs the same way
- Central place to set temperature, model, etc.
- Easy to swap providers later (Anthropic, Azure OpenAI, etc.)
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env in project root
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def complete(prompt: str, system: str = "You are a helpful engineer.", temperature: float = 0.2) -> str:
    """
    Send a simple system+user prompt to the chat model and return text.
    """
    resp = _client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return resp.choices[0].message.content
