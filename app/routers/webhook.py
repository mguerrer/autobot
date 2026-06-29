import json
import logging
from fastapi import APIRouter, Request, HTTPException
from app.schemas import WebhookIn
from app.config import settings
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


@router.post("/meta")
async def webhook_meta(request: Request):
    body = await request.json()
    logger.debug(f"Meta webhook recibido: {json.dumps(body, ensure_ascii=False)[:500]}")

    entry = body.get("entry", [])
    for ent in entry:
        for change in ent.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id", "")
            messages = value.get("messages", [])

            for msg in messages:
                if msg.get("type") != "text":
                    continue
                from_number = msg.get("from", "")
                text = msg.get("text", {}).get("body", "")
                message_id = msg.get("id", "")

                if not from_number or not text:
                    continue

                bot_whatsapp = await _buscar_bot_por_phone_number_id(phone_number_id)
                if not bot_whatsapp:
                    logger.warning(f"Phone Number ID {phone_number_id} no reconocido")
                    continue

                await procesar_mensaje_entrante(
                    bot_whatsapp=bot_whatsapp,
                    from_number=from_number,
                    texto=text,
                    message_id=message_id,
                )

    return {"status": "ok"}


@router.get("/whatsapp")
@router.get("/meta")
async def verificar_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode != "subscribe" or not token:
        raise HTTPException(status_code=403, detail="Verification failed")
    negocios = await cargar_negocios()
    for n in negocios:
        if n.get("verify_token") == token:
            return int(challenge) if challenge and challenge.isdigit() else challenge
    raise HTTPException(status_code=403, detail="Invalid verify_token")


@router.post("/baileys")
async def webhook_baileys(payload: WebhookIn):
    bot = payload.bot_whatsapp or settings.wa_bot_whatsapp
    if not bot:
        logger.warning("webhook_baileys: sin bot_whatsapp y sin WA_BOT_WHATSAPP configurado")
        return {"status": "ignored"}
    await procesar_mensaje_entrante(
        bot_whatsapp=bot,
        from_number=payload.from_number,
        texto=payload.message,
        message_id=payload.message_id,
    )
    return {"status": "ok"}


async def _buscar_bot_por_phone_number_id(phone_number_id: str) -> str | None:
    negocios = await cargar_negocios()
    for n in negocios:
        if n.get("phone_number_id") == phone_number_id:
            return n.get("bot_whatsapp")
    return None
