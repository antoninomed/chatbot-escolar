from app.config import settings
from app.storage.memory import recent_history

def ai_enabled() -> bool:
    return bool(settings.OPENAI_API_KEY)

async def generate_ai_reply(user_id: str, user_text: str) -> str | None:
    if not ai_enabled():
        return None

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        history = recent_history(user_id)
        input_msgs = [{"role": "system", "content": __import__("app.bot.prompts").bot.prompts.SYSTEM_PROMPT}]
        for m in history:
            input_msgs.append({"role": m.role, "content": m.content})
        input_msgs.append({"role": "user", "content": user_text})

        resp = await client.responses.create(
            model=settings.OPENAI_MODEL,
            input=input_msgs,
            max_output_tokens=220,
        )

        text = getattr(resp, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return None
    except Exception as e:
        print("AI error:", e)
        return None