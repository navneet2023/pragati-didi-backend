import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services.learner_service import (
    verify_learner_logic,
    get_learners_by_camp_logic,
)
from app.services.s3_service import log_json_to_s3

router = APIRouter(prefix="", tags=["Learner"])


@router.get("/verify-learner")
def verify_learner(
    learner_id: Optional[str] = Query(default=None),
    camp_id: Optional[str] = Query(default=None),
):
    log_json_to_s3(
        {
            "route": "/verify-learner",
            "learner_id": learner_id,
            "camp_id": camp_id,
            "timestamp": datetime.datetime.now().isoformat(),
        },
        prefix="fastapi-logs/learner",
    )

    result = verify_learner_logic(
        learner_id=learner_id or "",
        camp_id=camp_id or "",
    )
    return JSONResponse(status_code=result["status_code"], content=result["data"])


@router.get("/learners/{camp_id}")
def get_learners(camp_id: str):
    log_json_to_s3(
        {
            "route": "/learners",
            "camp_id": camp_id,
            "timestamp": datetime.datetime.now().isoformat(),
        },
        prefix="fastapi-logs/learner",
    )

    result = get_learners_by_camp_logic(camp_id)
    return JSONResponse(status_code=result["status_code"], content=result["data"])

