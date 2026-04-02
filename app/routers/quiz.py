from decimal import Decimal

from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.services.quiz_service import fetch_or_submit_quiz

router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.post("/question")
def quiz_question(payload: dict = Body(...)):
    result = fetch_or_submit_quiz(payload)

    safe_content = jsonable_encoder(
        result["data"],
        custom_encoder={
            Decimal: lambda v: int(v) if v % 1 == 0 else float(v)
        }
    )

    return JSONResponse(
        status_code=result["status_code"],
        content=safe_content
    )