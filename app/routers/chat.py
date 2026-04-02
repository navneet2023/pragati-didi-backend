from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.chat_service import generate_chat_response

router = APIRouter(tags=["Chat"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/chat-ui", response_class=HTMLResponse)
def chat_ui(request: Request):
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "title": "PragatiDidi Web Chat"},
    )


@router.post("/chat/message")
async def chat_message(request: Request):
    body = await request.json()

    message = body.get("message", "")
    learner_context = body.get("learner_context", {}) or {}

    response = generate_chat_response(message=message, learner_context=learner_context)

    return {
        "success": True,
        "reply": response["reply"],
        "next_action": response["next_action"],
    }