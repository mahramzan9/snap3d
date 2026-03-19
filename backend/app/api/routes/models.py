"""
snap3D — Models Router
GET  /models             — list user's models
GET  /models/{id}/download/{fmt}  — get download URL
DELETE /models/{id}      — delete model
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db, User, Model3D
from app.core.auth import get_current_user
from app.core import storage
router = APIRouter()
FORMAT_KEY_MAP = {"stl":"stl_key","obj":"obj_key","glb":"glb_key","ply":"ply_key"}
def _model_to_dict(m):
    return {"id":m.id,"name":m.name,"face_count":m.face_count,"file_size_mb":m.file_size_mb,"quality_score":m.quality_score,"is_watertight":m.is_watertight,"has_stl":bool(m.stl_key),"has_glb":bool(m.glb_key),"thumbnail_url":storage.generate_presigned_url(m.thumbnail_key) if m.thumbnail_key else None,"created_at":m.created_at.isoformat(),"task_id":m.task_id}
@router.get("")
async def list_models(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Model3D).where(Model3D.user_id == user.id).order_by(Model3D.created_at.desc()).limit(50))
    return [_model_to_dict(m) for m in result.scalars().all()]
@router.get("/{model_id}")
async def get_model(model_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Model3D).where(Model3D.id == model_id, Model3D.user_id == user.id))
    m = result.scalar_one_or_none()
    if not m: raise HTTPException(404, "Not found")
    return _model_to_dict(m)
@router.get("/{model_id}/download/{fmt}")
async def download_model(model_id: int, fmt: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    fmt = fmt.lower()
    if fmt not in FORMAT_KEY_MAP: raise HTTPException(400, "Bad format")
    result = await db.execute(select(Model3D).where(Model3D.id == model_id, Model3D.user_id == user.id))
    m = result.scalar_one_or_none()
    if not m: raise HTTPException(404, "Not found")
    key = getattr(m, FORMAT_KEY_MAP[fmt])
    if not key: raise HTTPException(404, "Format not available")
    return {"download_url": storage.generate_presigned_url(key, 300), "expires_in": 300, "format": fmt}
@router.patch("/{model_id}")
async def rename_model(model_id: int, body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Model3D).where(Model3D.id == model_id, Model3D.user_id == user.id))
    m = result.scalar_one_or_none()
    if not m: raise HTTPException(404, "Not found")
    if "name" in body: m.name = body["name"][:200]
    await db.commit()
    return {"ok": True}
@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Model3D).where(Model3D.id == model_id, Model3D.user_id == user.id))
    m = result.scalar_one_or_none()
    if not m: raise HTTPException(404, "Not found")
    for k in [m.stl_key, m.obj_key, m.glb_key, m.ply_key, m.thumbnail_key]:
        if k: storage.delete_file(k)
    await db.delete(m); await db.commit()
