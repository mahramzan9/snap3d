"""
snap3D — Task Routes
GET  /tasks/{id}         — poll task status (HTTP fallback)
WS   /tasks/{id}/ws      — WebSocket real-time progress stream
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import json
import redis.asyncio as aioredis
from app.core.database import get_db, User, ReconstructionTask
from app.core.auth import get_current_user
from app.core.redis_client import get_redis, get_cached_progress, PROGRESS_CHANNEL
router = APIRouter()
@router.get("")
async def list_tasks(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(ReconstructionTask).where(ReconstructionTask.user_id == user.id).order_by(ReconstructionTask.created_at.desc()).limit(20))
    return [{"id":t.id,"status":t.status,"progress":t.progress,"phase":t.phase,"quality":t.quality,\"image_count":"t.image_count,"created_at":t.created_at.isoformat()} for t in result.scalars().all()]
@router.get("/{task_id}")
async def get_task(task_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(ReconstructionTask).where(ReconstructionTask.id == task_id, ReconstructionTask.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task: raise HTTPException(404, "Not found")
    cached = await get_cached_progress(task_id)
    return {"id":task.id,"status":task.status,"progress":cached.get("progress") if cached else task.progress,"phase":cached.get("phase") if cached else task.phase,"error_msg":task.error_msg,"model_id":task.model.id if task.model else None}
@router.websocket("/{task_id}/ws")
async def task_progress_ws(task_id: int, websocket: WebSocket, token: str = ""):
    await websocket.accept()
    redis = await get_redis()
    channel = PROGRESS_CHANNEL.format(task_id=task_id)
    cached = await get_cached_progress(task_id)
    if cached: await websocket.send_text(json.dumps(cached))
    try:
        pubsub = redis.pubsub(); await pubsub.subscribe(channel)
        async def listen():
            async for msg in pubsub.listen():
                if msg["type"] != "message": continue
                data = json.loads(msg["data"])
                try: await websocket.send_text(json.dumps(data))
                except WebSocketDisconnect: return
                if data.get("status") in ("success", "failed"): return
        try: await asyncio.wait_for(listen(), timeout=900)
        except asyncio.TimeoutError: await websocket.send_text(json.dumps({"status":"timeout"}))
    except WebSocketDisconnect: pass
    finally:
        try: await pubsub.unsubscribe(channel); await pubsub.aclose()
        except: pass
