import logging
from fastapi import APIRouter, Request, HTTPException
from app.schemas import WebhookIn
from app.services.whatsapp_service import procesar_mensaje_entrante
from app.services.rule_engine import cargar_negocios

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/whatsapp")
async def webhook_whatsapp(payload: WebhookIn):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Mensaje vacío")
    await procesar_mensaje_entrante(
        bot_whatsapp=payload.bot_whatsapp,
        from_number=payload.from_number,
        texto=payload.message,
        message_id=payload.message_id,
    )
    return {"status": "ok"}


@router.get("/whatsapp")
async def verificar_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode != "subscribe" or not token:
        raise HTTPException(status_code=403, detail="Verification failed")
    negocios = cargar_negocios()
    for n in negocios:
        if n.get("verify_token") == token:
            return int(challenge) if challenge and challenge.isdigit() else challenge
    raise HTTPException(status_code=403, detail="Invalid verify_token")
