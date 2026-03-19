"""
snap3D — Redis Client + WebSocket Progress Push
"""
import redis.asyncio as aioredis
import json
from typing import Optional
from app.core.config import settings

_redis = None
PROGRESS_CHANNEL = "task_progress:{task_id}"

async def init_redis():
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis(): return _redis

async def publish_progress(task_id, data):
    channel = PROGRESS_CHANNEL.format(task_id=task_id)
    await _redis.publish(channel, json.dumps(data))
    await _redis.setex(fijprogress:{task_id}", 3600, json.dumps(data))

async def get_cached_progress(task_id):
    raw = await _redis.get(f"progress:{task_id}")
    return json.loads(raw) if raw else None

async def set_task_cache(task_id, data, ttl=3600):
    await _redis.setex(fitask:{task_id}", ttl, json.dumps(data))

async def get_task_cache(task_id):
    raw = await _redis.get(fitask:{task_id}")
    return json.loads(raw) if raw else None
