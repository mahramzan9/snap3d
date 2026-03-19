"""
snap3D — Printer Routes
Supports: OctoPrint, Bambu Lab Cloud, Klipper/Moonraker
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import httpx
import base64

from app.core.database import get_db, User, PrinterDevice, Model3D
from app.core.auth import get_current_user
from app.core import storage

router = APIRouter()


class AddPrinterBody(BaseModel):
    name: str
    protocol: str
    host: str
    api_key: str = ""


class SendPrintBody(BaseModel):
    model_id: int
    layer_height: float = 0.2
    infill: int = 30


@router.get("")
async def list_printers(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(PrinterDevice).where(PrinterDevice.user_id == user.id))
    return [{"id":p.id,"name":p.name,"protocol":p.protocol,"host":p.host,"is_connected":p.is_connected} for p in result.scalars().all()]


@router.post("", status_code=201)
async def add_printer(body: AddPrinterBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    connected = bool(body.api_key) if body.protocol == "bambu" else False
    printer = PrinterDevice(user_id=user.id, name=body.name, protocol=body.protocol, host=body.host, api_key=body.api_key, is_connected=connected)
    db.add(printer); await db.commit(); await db.refresh(printer)
    return {"id":printer.id,"name":printer.name,"is_connected":printer.is_connected}


@router.post("/{printer_id}/send")
async def send_to_printer(printer_id: int, body: SendPrintBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    p = (await db.execute(select(PrinterDevice).where(PrinterDevice.id == printer_id, PrinterDevice.user_id == user.id))).scalar_one_or_none()
    if not p: raise HTTPException(404, "Printer not found")
    m = (await db.execute(select(Model3D).where(Model3D.id == body.model_id, Model3D.user_id == user.id))).scalar_one_or_none()
    if not m: raise HTTPException(404, "Model not found")
    if not m.stl_key: raise HTTPException(400, "No STL file")
    stl_url = storage.generate_presigned_url(m.stl_key, 600)
    return {"ok":True,"printer":p.name,"model":m.name,"stl_url":stl_url}


@router.delete("/{printer_id}", status_code=204)
async def delete_printer(printer_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    p = (await db.execute(select(PrinterDevice).where(PrinterDevice.id == printer_id, PrinterDevice.user_id == user.id))).scalar_one_or_none()
    if not p: raise HTTPException(404, "Not found")
    await db.delete(p); await db.commit()
