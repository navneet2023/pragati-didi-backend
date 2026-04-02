from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.learner import router as learner_router
from app.routers.chat import router as chat_router
from app.routers.webhook import router as webhook_router
from app.routers.usage import router as usage_router
from app.routers.learning import router as learning_router
from app.routers.quiz import router as quiz_router
from app.routers.badge import router as badge_router

settings = get_settings()

app = FastAPI(title=settings.app_name)

# ✅ static serving
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(learner_router)
app.include_router(chat_router)
app.include_router(webhook_router)
app.include_router(usage_router)
app.include_router(learning_router)
app.include_router(quiz_router)
app.include_router(badge_router)


@app.get("/")
def home():
    return {
        "message": "PragatiDidi FastAPI is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}