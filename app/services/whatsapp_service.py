import abc
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models import Contacto, Conversacion, Mensaje
from app.services.rule_engine import construir_prompt_sistema, buscar_negocio_por_whatsapp
from app.services.ollama_service import generar_respuesta

logger = logging.getLogger(__name__)


class WhatsAppProvider(abc.ABC):
    @abc.abstractmethod
    async def send_message(self, to: str, message: str, bot_whatsapp: str):
        ...


class MockWhatsAppProvider(WhatsAppProvider):
    async def send_message(self, to: str, message: str, bot_whatsapp: str):
        logger.info(f"[MOCK] Enviando a {to} (bot: {bot_whatsapp}): {message}")
        print(f"\n---\n[{datetime.now(timezone.utc).isoformat()}] WhatsApp -> {to}:\n{message}\n---\n")


def get_provider() -> WhatsAppProvider:
    if settings.whatsapp_provider == "mock":
        return MockWhatsAppProvider()
    return MockWhatsAppProvider()


async def procesar_mensaje_entrante(bot_whatsapp: str, from_number: str, texto: str, message_id: str = ""):
    negocio = buscar_negocio_por_whatsapp(bot_whatsapp)
    if not negocio:
        logger.warning(f"Bot {bot_whatsapp} no encontrado o inactivo")
        return

    rut = negocio["rut"]
    provider = get_provider()

    async with async_session() as db:
        contacto = await _obtener_o_crear_contacto(db, from_number, rut)
        conversacion = await _obtener_o_crear_conversacion(db, contacto.id, rut)
        await _guardar_mensaje(db, conversacion.id, "user", texto)
        messages = await _obtener_historial(db, conversacion.id)

    system_prompt = construir_prompt_sistema(rut)
    respuesta = await generar_respuesta(system_prompt, messages)

    async with async_session() as db:
        await _guardar_mensaje(db, conversacion.id, "assistant", respuesta)

    await provider.send_message(from_number, respuesta, bot_whatsapp)


async def _obtener_o_crear_contacto(db: AsyncSession, telefono: str, negocio_rut: str) -> Contacto:
    stmt = select(Contacto).where(
        Contacto.telefono == telefono,
        Contacto.negocio_rut == negocio_rut,
    )
    result = await db.execute(stmt)
    contacto = result.scalar_one_or_none()
    if not contacto:
        contacto = Contacto(telefono=telefono, negocio_rut=negocio_rut)
        db.add(contacto)
        await db.commit()
        await db.refresh(contacto)
    return contacto


async def _obtener_o_crear_conversacion(db: AsyncSession, contacto_id: int, negocio_rut: str) -> Conversacion:
    stmt = select(Conversacion).where(
        Conversacion.contacto_id == contacto_id,
        Conversacion.negocio_rut == negocio_rut,
        Conversacion.estado == "activa",
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversacion(contacto_id=contacto_id, negocio_rut=negocio_rut)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv


async def _guardar_mensaje(db: AsyncSession, conversacion_id: int, rol: str, contenido: str) -> Mensaje:
    msg = Mensaje(conversacion_id=conversacion_id, rol=rol, contenido=contenido)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def _obtener_historial(db: AsyncSession, conversacion_id: int, limite: int = 20) -> list[dict]:
    stmt = (
        select(Mensaje)
        .where(Mensaje.conversacion_id == conversacion_id)
        .order_by(Mensaje.created_at.desc())
        .limit(limite)
    )
    result = await db.execute(stmt)
    msgs = result.scalars().all()
    return [{"rol": m.rol, "contenido": m.contenido} for m in reversed(msgs)]
