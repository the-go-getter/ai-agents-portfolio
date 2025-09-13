import os
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# If using OpenAI's responses API (chat completions-style):

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def complete(prompt: str, system: str = "You are a helpful engineer.") -> str:
    rsp = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return rsp.choices[0].message.content
