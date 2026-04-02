import datetime

from fastapi import APIRouter, Request

from app.services.turn_service import parse_turn_webhook, build_turn_reply
from app.services.chat_service import generate_chat_response
from app.services.s3_service import log_json_to_s3

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/turn")
async def turn_webhook(request: Request):
    payload = await request.json()

    log_json_to_s3(
        {
            "route": "/webhook/turn",
            "timestamp": datetime.datetime.now().isoformat(),
            "payload": payload,
        },
        prefix="fastapi-logs/turn",
    )

    turn_data = parse_turn_webhook(payload)
    chat_result = generate_chat_response(message=turn_data.get("text", ""))

    return build_turn_reply(chat_result["reply"])