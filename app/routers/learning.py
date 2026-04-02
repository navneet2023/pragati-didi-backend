import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body
from fastapi.responses import JSONResponse

from app.services.s3_service import log_json_to_s3
from app.services.learning_service import fetch_phases_or_chapters, fetch_subject_chapter_rows, fetch_quiz_questions
from app.services.content_service import fetch_learning_content
from app.services.log_service import log_learning_action


router = APIRouter(prefix="/learning", tags=["Learning"])


@router.get("/chapters")
def get_chapters(
    state: Optional[str] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    phase: Optional[str] = Query(default=None),
):
    log_json_to_s3(
        {
            "route": "/learning/chapters",
            "state": state,
            "subject": subject,
            "phase": phase,
            "timestamp": datetime.datetime.now().isoformat(),
        },
        prefix="fastapi-logs/learning/chapters",
    )

    result = fetch_phases_or_chapters(
        state=state or "",
        subject=subject or "",
        phase=phase or "",
    )
    return JSONResponse(status_code=result["status_code"], content=result["data"])


@router.get("/content")
def get_learning_content(
    state: Optional[str] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    chapter: Optional[str] = Query(default=None),
    mobile: Optional[str] = Query(default=None),
    learner_id: Optional[str] = Query(default=None),
    camp_id: Optional[str] = Query(default=None),
):
    log_json_to_s3(
        {
            "route": "/learning/content",
            "state": state,
            "subject": subject,
            "chapter": chapter,
            "mobile": mobile,
            "learner_id": learner_id,
            "camp_id": camp_id,
            "timestamp": datetime.datetime.now().isoformat(),
        },
        prefix="fastapi-logs/learning/content",
    )

    result = fetch_learning_content(
        state=state or "",
        subject=subject or "",
        chapter=chapter or "",
        mobile=mobile or "",
        learner_id=learner_id or "",
        camp_id=camp_id or "",
    )
    return JSONResponse(status_code=result["status_code"], content=result["data"])


@router.post("/log-action")
def log_action(payload: dict = Body(...)):
    result = log_learning_action(payload)
    return JSONResponse(status_code=200, content=result)

@router.get("/subject-chapters/{state}")
def get_subject_chapters(state: str):
    log_json_to_s3(
        {
            "route": "/learning/subject-chapters",
            "state": state,
            "timestamp": datetime.datetime.now().isoformat(),
        },
        prefix="fastapi-logs/learning/subject-chapters",
    )

    result = fetch_subject_chapter_rows(state=state or "")
    return JSONResponse(status_code=result["status_code"], content=result["data"])

@router.get("/quiz")
def get_quiz_questions(
    state: Optional[str] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    chapter: Optional[str] = Query(default=None),
):
    result = fetch_quiz_questions(
        state=state or "",
        subject=subject or "",
        chapter=chapter or "",
    )
    return JSONResponse(status_code=result["status_code"], content=result["data"])