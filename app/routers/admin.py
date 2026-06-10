import httpx
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Conversacion, Contacto, Mensaje
from app.services.rule_engine import cargar_negocios, cargar_rubros, guardar_negocios

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


@router.get("/negocios/{rut}/editar", response_class=HTMLResponse)
async def admin_negocio_editar(request: Request, rut: str):
    negocios = cargar_negocios()
    rubros = cargar_rubros()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)
    return templates.TemplateResponse(request, "negocio_edit.html", {
        "negocio": negocio,
        "rubros": rubros,
    })


@router.post("/negocios/{rut}/editar")
async def admin_negocio_guardar(request: Request, rut: str):
    negocios = cargar_negocios()
    rubros = cargar_rubros()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)

    form = await request.form()
    negocio["nombre"] = form.get("nombre", negocio["nombre"])
    negocio["dueno_nombre"] = form.get("dueno_nombre", negocio["dueno_nombre"])
    negocio["dueno_telefono"] = form.get("dueno_telefono", negocio["dueno_telefono"])
    negocio["bot_whatsapp"] = form.get("bot_whatsapp", negocio["bot_whatsapp"])
    negocio["verify_token"] = form.get("verify_token", negocio.get("verify_token", ""))
    negocio["phone_number_id"] = form.get("phone_number_id", negocio.get("phone_number_id", ""))
    try:
        negocio["rubro_id"] = int(form.get("rubro_id", negocio["rubro_id"]))
    except (ValueError, TypeError):
        pass
    negocio["activo"] = form.get("activo") == "on"

    guardar_negocios(negocios)
    return RedirectResponse(url=f"/admin/negocios/{rut}", status_code=303)


@router.post("/negocios/{rut}/toggle")
async def admin_negocio_toggle(request: Request, rut: str):
    negocios = cargar_negocios()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)
    negocio["activo"] = not negocio["activo"]
    guardar_negocios(negocios)
    return RedirectResponse(url="/admin/negocios", status_code=303)


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


@router.get("/chats/{conv_id}", response_class=HTMLResponse)
async def admin_chat_detail(request: Request, conv_id: int, db: AsyncSession = Depends(get_db)):
    negocios = {n["rut"]: n["nombre"] for n in cargar_negocios()}

    result = await db.execute(
        select(Conversacion, Contacto)
        .join(Contacto, Conversacion.contacto_id == Contacto.id)
        .where(Conversacion.id == conv_id)
    )
    row = result.one_or_none()
    if not row:
        return HTMLResponse("Conversación no encontrada", status_code=404)

    conv, contacto = row

    msgs_result = await db.execute(
        select(Mensaje).where(Mensaje.conversacion_id == conv.id).order_by(Mensaje.created_at)
    )
    mensajes = msgs_result.scalars().all()

    return templates.TemplateResponse(request, "conversacion_detail.html", {
        "conversacion": conv,
        "contacto_nombre": contacto.nombre or "",
        "contacto_telefono": contacto.telefono,
        "negocio_nombre": negocios.get(conv.negocio_rut, conv.negocio_rut),
        "mensajes": mensajes,
    })


@router.post("/chats/{conv_id}/responder")
async def admin_chat_responder(request: Request, conv_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.whatsapp_service import get_provider

    result = await db.execute(
        select(Conversacion, Contacto)
        .join(Contacto, Conversacion.contacto_id == Contacto.id)
        .where(Conversacion.id == conv_id)
    )
    row = result.one_or_none()
    if not row:
        return HTMLResponse("Conversación no encontrada", status_code=404)

    conv, contacto = row

    form = await request.form()
    texto = form.get("mensaje", "").strip()
    if not texto:
        return RedirectResponse(url=f"/admin/chats/{conv_id}", status_code=303)

    msg = Mensaje(conversacion_id=conv.id, rol="assistant", contenido=texto)
    db.add(msg)
    await db.commit()

    provider = get_provider()
    await provider.send_message(contacto.telefono, texto, "")

    return RedirectResponse(url=f"/admin/chats/{conv_id}", status_code=303)


@router.get("/wa-bridge", response_class=HTMLResponse)
async def admin_wa_bridge(request: Request):
    bridge_url = settings.wa_bridge_url
    sessions_data = []
    error = None

    if bridge_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{bridge_url}/status")
                data = resp.json()
                sessions_data = data.get("sessions", [])
        except httpx.RequestError as e:
            error = str(e)

        for s in sessions_data:
            if s.get("state") == "awaiting_qr" and s.get("hasQR"):
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        qr_resp = await client.get(f"{bridge_url}/qr/{s['numero']}")
                        s["qr_data"] = qr_resp.json().get("qr")
                except httpx.RequestError:
                    s["qr_data"] = None

    return templates.TemplateResponse(request, "wa_bridge.html", {
        "sessions": sessions_data,
        "error": error,
        "bridge_url": bridge_url,
    })
