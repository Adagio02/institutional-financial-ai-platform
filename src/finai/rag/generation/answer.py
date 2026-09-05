from finai.core.config import get_settings


def answer_question(question: str, tickers: list[str] | None = None) -> dict[str, object]:
    settings = get_settings()
    if not question.strip():
        return {"answer": "A question is required.", "citations": []}
    if not settings.openai_api_key:
        return {
            "answer": "OPENAI_API_KEY is not configured. Retrieval can still be evaluated separately.",
            "citations": [],
        }
    return {
        "answer": "Connect retrieval results and the OpenAI Responses API in this module.",
        "citations": [],
        "tickers": tickers or [],
    }
