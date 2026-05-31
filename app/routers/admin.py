from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversacion, Contacto, Mensaje
from app.services.rule_engine import cargar_negocios, cargar_rubros

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request, db: AsyncSession = Depends(get_db)):
    negocios = cargar_negocios()
    rubros = {r["id"]: r["nombre"] for r in cargar_rubros()}

    result = await db.execute(select(Conversacion).order_by(desc(Conversacion.updated_at)).limit(10))
    conversaciones = result.scalars().all()

    convs = []
    for c in conversaciones:
        cr = await db.execute(select(Contacto).where(Contacto.id == c.contacto_id))
        contacto = cr.scalar_one_or_none()
        negocio = next((n for n in negocios if n["rut"] == c.negocio_rut), None)
        convs.append({
            "id": c.id,
            "contacto": f"{contacto.nombre or ''} ({contacto.telefono})" if contacto else "?",
            "negocio": negocio["nombre"] if negocio else c.negocio_rut,
            "estado": c.estado,
        })

    return templates.TemplateResponse(request, "index.html", {
        "negocios": negocios,
        "rubros": rubros,
        "conversaciones": convs,
        "total_negocios": len(negocios),
        "total_conversaciones": len(conversaciones),
    })


@router.get("/negocios", response_class=HTMLResponse)
async def admin_negocios(request: Request):
    negocios = cargar_negocios()
    rubros = {rub["id"]: rub for rub in cargar_rubros()}
    return templates.TemplateResponse(request, "negocios.html", {
        "negocios": negocios,
        "rubros": rubros,
    })


@router.get("/negocios/{rut}", response_class=HTMLResponse)
async def admin_negocio_detail(request: Request, rut: str, db: AsyncSession = Depends(get_db)):
    negocios = cargar_negocios()
    rubros = {rub["id"]: rub for rub in cargar_rubros()}
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)

    result = await db.execute(
        select(Conversacion).where(Conversacion.negocio_rut == rut).order_by(desc(Conversacion.updated_at))
    )
    conversaciones = result.scalars().all()
    convs = []
    for c in conversaciones:
        cr = await db.execute(select(Contacto).where(Contacto.id == c.contacto_id))
        contacto = cr.scalar_one_or_none()
        sub = await db.execute(select(Mensaje).where(Mensaje.conversacion_id == c.id).order_by(desc(Mensaje.created_at)).limit(1))
        ultimo = sub.scalar_one_or_none()
        convs.append({
            "id": c.id,
            "contacto": f"{contacto.nombre or ''} ({contacto.telefono})" if contacto else "?",
            "estado": c.estado,
            "ultimo_mensaje": (ultimo.contenido[:100] + "...") if ultimo else "",
        })

    return templates.TemplateResponse(request, "negocio_detail.html", {
        "negocio": negocio,
        "rubro": rubros.get(negocio["rubro_id"]),
        "conversaciones": convs,
    })


@router.get("/chats", response_class=HTMLResponse)
async def admin_chats(request: Request, db: AsyncSession = Depends(get_db)):
    negocios = {n["rut"]: n["nombre"] for n in cargar_negocios()}
    result = await db.execute(
        select(Conversacion, Contacto.telefono, Contacto.nombre)
        .join(Contacto, Conversacion.contacto_id == Contacto.id)
        .order_by(desc(Conversacion.updated_at))
    )
    rows = result.all()
    conversaciones = []
    for conv, tel, nom in rows:
        sub = await db.execute(
            select(Mensaje.contenido).where(Mensaje.conversacion_id == conv.id)
            .order_by(desc(Mensaje.created_at)).limit(1)
        )
        ultimo = sub.scalar_one_or_none() or ""
        conversaciones.append({
            "id": conv.id,
            "contacto": f"{nom or ''} ({tel})",
            "negocio": negocios.get(conv.negocio_rut, conv.negocio_rut),
            "estado": conv.estado,
            "ultimo_mensaje": ultimo[:120],
        })
    return templates.TemplateResponse(request, "chats.html", {
        "conversaciones": conversaciones,
    })
