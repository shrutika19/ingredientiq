from fastapi import APIRouter

from app.api.routes import health, submissions
from app.api.routes.analysis import router as analysis_router


api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(submissions.router)
api_router.include_router(analysis_router)