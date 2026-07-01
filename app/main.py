from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.api.codes import router as agent_router
from app.api.auth import router as auth_router
from app.core.config import settings

app = FastAPI(title="nascent api")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="none",
    https_only=True, 
    max_age=60 * 60 * 24 * 7
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        settings.frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    agent_router,
    prefix="/api",
    tags=["agent"]
)

app.include_router(
    auth_router,
    prefix="/api",
    tags=["auth"]
)