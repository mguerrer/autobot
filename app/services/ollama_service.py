import ollama
from app.config import settings


_client = None


def get_client():
    global _client
    if _client is None:
        _client = ollama.AsyncClient(host=settings.ollama_url)
    return _client


def _options():
    opts = {"temperature": 0.7, "max_tokens": 500, "num_gpu": 0}
    return opts


async def generar_respuesta(system_prompt: str, historial: list[dict]) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    for msg in historial:
        messages.append({"role": msg["rol"], "content": msg["contenido"]})

    client = get_client()
    response = await client.chat(
        model=settings.ollama_model,
        messages=messages,
        options=_options(),
    )
    return response["message"]["content"]
