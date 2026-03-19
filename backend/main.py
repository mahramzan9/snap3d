"""
snap3D Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import auth, upload, tasks, models, printers
from app.core.config import settings
from app.core.database import init_db
from app.core.redis_client import init_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_redis()
    yield

app = FastAPI(title="snap3D API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(models.router, prefix="/api/v1/models", tags=["Models"])
app.include_router(printers.router, prefix="/api/v1/printers", tags=["Printers"])

@app.get("/health")
async def health(): return {"status": "ok"}
