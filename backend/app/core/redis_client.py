"""snap3D — Redis Client"""
import redis.asyncio as aioredis
import json
from typing import Optional
from app.core.config import settings

_redis: Optional[aioredis.Redis] = None
PROGRESS_CHANNEL = "task_progress:{task_id}"

async def init_redis():
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis() -> aioredis.Redis:
    return _redis

async def publish_progress(task_id: int, data: dict):
    channel = PROGRESS_CHANNEL.format(task_id=task_id)
    await _redis.publish(channel, json.dumps(data))
    await _redis.setex(f"progress:{task_id}", 3600, json.dumps(data))

async def get_cached_progress(task_id: int) -> Optional[dict]:
    raw = await _redis.get(f"progress:{task_id}")
    return json.loads(raw) if raw else None
