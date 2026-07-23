from fastapi import APIRouter
from finai.rag.generation.answer import answer_question

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query")
def query(payload: dict) -> dict[str, object]:
    return answer_question(str(payload.get("question", "")), payload.get("tickers"))
