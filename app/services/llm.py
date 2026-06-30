from app.core.config import settings

from groq import AsyncGroq
import json

_client: AsyncGroq | None = None

def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)

    return _client

async def call_llm(prompt):
    response = await _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant, always provide the answer in JSON format."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0
    )

    content = response.choices[0].message.content

    if content is None:
        raise ValueError("LLM returned no content.")

    return json.loads(content)