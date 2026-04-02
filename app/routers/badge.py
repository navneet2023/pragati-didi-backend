from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.services.badge_service import generate_badge

router = APIRouter(prefix="/badge", tags=["Badge"])


@router.post("/appreciation")
def badge_appreciation(payload: dict = Body(...)):
    result = generate_badge(payload)
    return JSONResponse(status_code=result["status_code"], content=result["data"])