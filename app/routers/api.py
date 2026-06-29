from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Conversacion, Contacto, Mensaje
from app.schemas import ConversacionOut, MensajeOut
from app.services.rule_engine import cargar_negocios, cargar_rubros

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/negocios")
async def listar_negocios():
    negocios = await cargar_negocios()
    rubros = {r["id"]: r["nombre"] for r in cargar_rubros()}
    result = []
    for n in negocios:
        result.append({
            "rut": n["rut"],
            "nombre": n["nombre"],
            "rubro_id": n["rubro_id"],
            "rubro_nombre": rubros.get(n["rubro_id"], ""),
            "dueno_nombre": n["dueno_nombre"],
            "dueno_telefono": n["dueno_telefono"],
            "bot_whatsapp": n["bot_whatsapp"],
            "activo": n["activo"],
        })
    return result


@router.get("/conversaciones")
async def listar_conversaciones(
    negocio_rut: str = Query(""),
    estado: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    negocios_list = await cargar_negocios()
    negocios = {n["rut"]: n["nombre"] for n in negocios_list}
    stmt = select(
        Conversacion,
        Contacto.telefono,
        Contacto.nombre,
    ).join(Contacto, Conversacion.contacto_id == Contacto.id)

    if negocio_rut:
        stmt = stmt.where(Conversacion.negocio_rut == negocio_rut)
    if estado:
        stmt = stmt.where(Conversacion.estado == estado)
    stmt = stmt.order_by(desc(Conversacion.updated_at))

    result = await db.execute(stmt)
    rows = result.all()

    conversaciones = []
    for conv, tel, nom in rows:
        sub = await db.execute(
            select(Mensaje.contenido)
            .where(Mensaje.conversacion_id == conv.id)
            .order_by(desc(Mensaje.created_at))
            .limit(1)
        )
        ultimo = sub.scalar_one_or_none() or ""
        conversaciones.append(ConversacionOut(
            id=conv.id,
            contacto_telefono=tel,
            contacto_nombre=nom or "",
            negocio_rut=conv.negocio_rut,
            negocio_nombre=negocios.get(conv.negocio_rut, ""),
            estado=conv.estado,
            ultimo_mensaje=ultimo[:120],
            updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
        ))
    return conversaciones


@router.get("/conversaciones/{conv_id}/mensajes")
async def ver_mensajes(conv_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Mensaje).where(Mensaje.conversacion_id == conv_id).order_by(Mensaje.created_at)
    result = await db.execute(stmt)
    msgs = result.scalars().all()
    return [MensajeOut(
        id=m.id,
        rol=m.rol,
        contenido=m.contenido,
        created_at=m.created_at.isoformat() if m.created_at else "",
    ) for m in msgs]
