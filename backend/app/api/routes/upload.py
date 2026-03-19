"""
snap3D — Upload Routes
POST /upload/images  — accepts multipart images, uploads to S3, creates task, queues Celery job
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import json
from app.core.database import get_db, User, ReconstructionTask, TaskStatus
from app.core.auth import get_current_user
from app.core.config import settings
from app.core import storage
from app.worker.tasks import reconstruct_3d
router = APIRouter()
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
@router.post("/images")
async def upload_images(files: List[UploadFile] = File(...), quality: str = Form("standard"), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if len(files) == 0: raise HTTPException(400, "请 at least one image")
    if quality not in ("fast", "standard", "high"): quality = "standard"
    task = ReconstructionTask(user_id=user.id, status=TaskStatus.UPLOADING, quality=quality, image_count=len(files), provider=settings.RECONSTRUCTION_PROVIDER)
    db.add(task); await db.commit(); await db.refresh(task)
    image_keys = []
    for f in files:
        if f.content_type not in ALLOWED_TYPES: raise HTTPException(400, f"Bad type: {f.content_type}")
        content = await f.read()
        import io
        key = storage.make_image_key(user.id, task.id, f.filename or "img.jpg")
        storage.upload_file(io.BytesIO(content), key, content_type=f.content_type)
        image_keys.append(key)
    task.image_keys = json.dumps(image_keys); task.status = TaskStatus.QUEUED
    await db.commit()
    r = reconstruct_3d.delay(task.id, image_keys, quality)
    task.celery_id = r.id; await db.commit()
    return {"task_id": task.id, "status": "queued"}
