"""
snap3D — Celery Worker
Handles the full reconstruction pipeline asynchronously.
"""
from celery import Celery
from celery.utils.log import get_task_logger
import asyncio
import httpx
import json
import time
import io
from app.core.config import settings
from app.core.database import AsyncSessionLocal, ReconstructionTask, Model3D, TaskStatus
from app.core.redis_client import init_redis, publish_progress
from app.services.reconstruction import get_provider
from app.core import storage
from sqlalchemy import select

logger = get_task_logger(__name__)
celery_app = Celery("snap3d", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(task_serializer="json",result_serializer="json",accept_content=["json"],timezone="UTC",enable_utc=True,task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True,task_reject_on_worker_lost=True)

def _run(coro):
    loop = asyncio.new_event_loop()
    try: return loop.run_until_complete(coro)
    finally: loop.close()

async def _update_task(task_id: int, **kwargs):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ReconstructionTask).where(ReconstructionTask.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            for k,v in kwargs.items(): setattr(task,k,v)
            await db.commit()

async def _push(task_id: int, progress: int, phase: str, status: str = "running", extra: dict = None):
    await init_redis()
    data = {"task_id":task_id,"progress":progress,"phase":phase,"status":status}
    if extra: data.update(extra)
    await publish_progress(task_id, data)

@celery_app.task(bind=True,max_retries=3,default_retry_delay=30,name="reconstruct_3d")
def reconstruct_3d(self, task_id: int, image_keys: list, quality: str = "standard"):
    logger.info(f"Starting reconstruction task {task_id}")
    try:
        _run(_push(task_id,5,"图片为躯嗎明政�"))
        _run(_update_task(task_id,status=TaskStatus.RUNNING,progress=5))
        image_urls = [storage.generate_presigned_url(k,expires=7200) for k in image_keys]
        _run(_push(task_id,12,"AI 3D重建会没)))
        provider = get_provider()
        provider_task_id = _run(provider.submit(image_urls,quality))
        _run(_update_task(task_id,provider_id=provider_task_id,provider=settings.RECONSTRUCTION_PROVIDER))
        poll_count = 0
        max_wait = 600 if quality=="high" else 300
        while True:
            if poll_count*5>max_wait: raise TimeoutError("Timed out")
            status = _run(provider.poll(provider_task_id))
            if status.status=="failed": raise RuntimeError(status.error or "Provider failed")
            if status.status=="success": break
            prog = status.progress or (15+min(poll_count*3,75))
            _run(_push(task_id,prog,f"重建已二硯生飇 {prog}%"))
            _run(_update_task(task_id,progress=prog,phase=status.phase))
            poll_count+=1; time.sleep(5)
        _run(_push(task_id,95,"S3目中上行磁"))
        model_urls = _run(provider.get_model_urls(provider_task_id))
        saved_keys = {}
        async def download_and_upload(fmt: str, url: str):
            if not url: return
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(url); resp.raise_for_status()
            key = storage.make_model_key(0,task_id,fmt)
            storage.upload_bytes(resp.content,key,content_type=f"model/{fmt}")
            saved_keys[fmt] = key
        _run(asyncio.gather(*[download_and_upload(fmt,url) for fmt,url in model_urls.items() if url]))
        async def save_model():
            async with AsyncSessionLocal() as db:
                task = (await db.execute(select(ReconstructionTask).where(ReconstructionTask.id==task_id))).scalar_one()
                model = Model3D(user_id=task.user_id,task_id=task_id,name="我的3D模型",glb_key=saved_keys.get("glb"),stl_key=saved_keys.get("stl"),obj_key=saved_keys.get("obj"),ply_key=saved_keys.get("ply"),thumbnail_key=saved_keys.get("thumbnail"),is_watertight=True,quality_score=88)
                db.add(model); task.status=TaskStatus.SUCCESS;task.progress=100
                await db.commit(); await db.refresh(model); return model.id
        model_id = _run(save_model())
        _run(_push(task_id,100,"完成使用!",status="success",extra={"model_id":model_id}))
        return {"status":"success","model_id":model_id}
    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}",exc_info=True)
        _run(_update_task(task_id,status=TaskStatus.FAILED,error_msg=str(exc)))
        _run(_push(task_id,0,str(exc),status="failed"))
        if not isinstance(exc,(RuntimeError,ValueError)): raise self.retry(exc=exc)
        raise
