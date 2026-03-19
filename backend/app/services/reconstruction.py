"""
nap3D Reconstruction Provider
"""
import httpx
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict
from app.core.config import settings


@dataclass
class ProviderStatus:
    provider_task_id: str
    status: str
    progress: int
    phase: str
    model_url: Optional[str] = None
    error: Optional[str] = None


class ReconstructionProvider(ABC):
    @abstractmethod
    async def submit(self, image_urls: List[str], quality: str) -> str:
        pass

    @abstractmethod
    async def poll(self, provider_task_id: str) -> ProviderStatus:
        pass

    @abstractmethod
    async def get_model_urls(self, provider_task_id: str) -> Dict[str, str]:
        pass


class Tripo3DProvider(ReconstructionProvider):
    """Tripo3D API v2 - https://platform.tripo3d.ai/docs"""
    BASE = settings.TRIPO3D_BASE_URL
    QUALITY_MAP = {"fast": "draft", "standard": "detailed", "high": "refined"}

    async def submit(self, image_urls: List[str], quality: str = "standard") -> str:
        mode = self.QUALITY_MAP.get(quality, "detailed")
        if len(image_urls) == 1:
            payload = {"type": "image_to_model", "file": {"type": "url", "url": image_urls[0]}, "model_version": "v2.0-20240919", "quality": mode}
        else:
            payload = {"type": "multiview_to_model", "files": [{"type": "url", "url": u} for u in image_urls[:20]], "model_version": "v2.0-20240919", "quality": mode}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.BASE}/task", headers={"Authorization": f"Bearer {settings.TRIPO3D_API_KEY}"}, json=payload)
            resp.raise_for_status()
            return resp.json()["data"]["task_id"]

    async def poll(self, provider_task_id: str) -> ProviderStatus:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.BASE}/task/{provider_task_id}", headers={"Authorization": f"Bearer {settings.TRIPO3D_API_KEY}"})
            resp.raise_for_status()
            d = resp.json()["data"]
        status_map = {"queued": ("queued", 5, "Queued"), "running": ("running", 50, "Running"), "success": ("success", 100, "Done"), "failed": ("failed", 0, "Failed")}
        st, prog, phase = status_map.get(d["status"], ("running", 30, "Processing"))
        if d["status"] == "running":
            prog = d.get("progress", 30)
        return ProviderStatus(provider_task_id=provider_task_id, status=st, progress=prog, phase=phase, model_url=d.get("output", {}).get("model") if st == "success" else None, error=d.get("message") if st == "failed" else None)

    async def get_model_urls(self, provider_task_id: str) -> Dict[str, str]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.BASE}/task/{provider_task_id}", headers={"Authorization": f"Bearer {settings.TRIPO3D_API_KEY}"})
            resp.raise_for_status()
            output = resp.json()["data"].get("output", {})
        urls = {}
        if output.get("model"): urls["glb"] = output["model"]
        if output.get("rendered_image"): urls["thumbnail"] = output["rendered_image"]
        return urls


class MeshyProvider(ReconstructionProvider):
    """Meshy API v2 - https://docs.meshy.ai"""
    BASE = settings.MESHY_BASE_URL

    async def submit(self, image_urls: List[str], quality: str = "standard") -> str:
        payload = {"image_url": image_urls[0], "enable_pbr": True, "ai_model": "meshy-4", "topology": "quad", "target_polycount": 30000 if quality == "fast" else 80000}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.BASE}/image-to-3d", headers={"Authorization": f"Bearer {settings.MESHY_API_KEY}"}, json=payload)
            resp.raise_for_status()
            return resp.json()["result"]

    async def poll(self, provider_task_id: str) -> ProviderStatus:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.BASE}/image-to-3d/{provider_task_id}", headers={"Authorization": f"Bearer {settings.MESHY_API_KEY}"})
            resp.raise_for_status()
            d = resp.json()
        map_ = {"PENDING": ("queued", 5, "Queued"), "IN_PROGRESS": ("running", d.get("progress", 30), "Processing"), "SUCCEEDED": ("success", 100, "Done"), "FAILED": ("failed", 0, "Failed")}
        st, prog, phase = map_.get(d.get("status", "PENDING"), ("running", 30, "Processing"))
        return ProviderStatus(provider_task_id=provider_task_id, status=st, progress=prog, phase=phase, model_url=d.get("model_urls", {}).get("glb") if st == "success" else None, error=d.get("message") if st == "failed" else None)

    async def get_model_urls(self, provider_task_id: str) -> Dict[str, str]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.BASE}/image-to-3d/{provider_task_id}", headers={"Authorization": f"Bearer {settings.MESHY_API_KEY}"})
            resp.raise_for_status()
            urls = resp.json().get("model_urls", {})
        return {"glb": urls.get("glb", ""), "stl": urls.get("stl", ""), "obj": urls.get("obj", ""), "thumbnail": resp.json().get("thumbnail_url", "")}


def get_provider() -> ReconstructionProvider:
    p = settings.RECONSTRUCTION_PROVIDER
    if p == "meshy": return MeshyProvider()
    return Tripo3DProvider()
