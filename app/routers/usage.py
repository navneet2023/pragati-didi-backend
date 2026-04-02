import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services.s3_service import log_json_to_s3
from app.services.usage_service import build_welcome_payload

router = APIRouter(tags=["Usage"])


@router.get("/welcome-message")
def welcome_message(
    learner_id: Optional[str] = Query(default=None),
    camp_id: Optional[str] = Query(default=None),
    mobile: Optional[str] = Query(default=None),
    learner_name: Optional[str] = Query(default=None),
):
    log_json_to_s3(
        {
            "route": "/welcome-message",
            "learner_id": learner_id,
            "camp_id": camp_id,
            "mobile": mobile,
            "learner_name": learner_name,
            "timestamp": datetime.datetime.now().isoformat(),
        },
        prefix="fastapi-logs/welcome-message",
    )

    result = build_welcome_payload(
        learner_id=learner_id or "",
        camp_id=camp_id or "",
        mobile=mobile or "",
        learner_name=learner_name or "",
    )

    return JSONResponse(status_code=200, content=result)