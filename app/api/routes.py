from fastapi import APIRouter, HTTPException
from app.services.whatsapp import service
from app.api.models import MessageSend
import asyncio

router = APIRouter()

@router.get("/status")
async def get_status():
    status = await service.get_status()
    return {"status": status}

@router.get("/qr")
async def get_qr():
    status = await service.get_status()
    if status == "connected":
        return {"status": "connected", "qr": None}
    
    qr_base64 = await service.get_qr()
    if not qr_base64:
        raise HTTPException(status_code=404, detail="QR Code not found (yet)")
    
    return {"status": "waiting_qr", "qr_base64": qr_base64}

@router.post("/send")
async def send_message(payload: MessageSend):
    success = await service.send_message(payload.phone_number, payload.message, payload.image_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send message")
    return {"status": "sent", "to": payload.phone_number}
