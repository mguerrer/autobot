from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversacion, Contacto, Mensaje
from app.services.rule_engine import (
    cargar_negocios_db, guardar_negocios_db,
    cargar_reglas_generales, cargar_reglas_negocio, guardar_reglas_negocio,
    cargar_numeros_whatsapp, eliminar_numero_whatsapp,
    obtener_aviso_cuenta_personal, marcar_aviso_personal_visto, aviso_personal_fue_visto,
)
from app.auth import (
    get_session, ensure_authenticated, has_role, user_context,
)

router = APIRouter(prefix="/cliente", tags=["cliente"])
templates = Jinja2Templates(directory="app/templates")


def _check_cliente(session: dict, rut: str):
    if not has_role(session, "cliente"):
        return False
    return session.get("negocio_rut") == rut


@router.get("/", response_class=HTMLResponse)
async def cliente_index(request: Request):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")
    negocios = await cargar_negocios_db()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)

    reglas = await cargar_reglas_negocio(rut)
    numeros = await cargar_numeros_whatsapp(rut)

    return templates.TemplateResponse(request, "cliente/index.html", {
        "negocio": negocio,
        "numeros": numeros,
        "reglas": reglas,
        **user_context(request),
        "pagina": "dashboard",
    })


@router.get("/conversaciones", response_class=HTMLResponse)
async def cliente_conversaciones(request: Request, db: AsyncSession = Depends(get_db)):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")
    negocios_list = await cargar_negocios_db()
    negocios = {n["rut"]: n["nombre"] for n in negocios_list}

    result = await db.execute(
        select(Conversacion, Contacto.telefono, Contacto.nombre)
        .join(Contacto, Conversacion.contacto_id == Contacto.id)
        .where(Conversacion.negocio_rut == rut)
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
            "estado": conv.estado,
            "ultimo_mensaje": ultimo[:120],
        })

    return templates.TemplateResponse(request, "cliente/conversaciones.html", {
        "conversaciones": conversaciones,
        "negocio": negocios.get(rut, rut),
        **user_context(request),
        "pagina": "conversaciones",
    })


@router.get("/conversaciones/{conv_id}", response_class=HTMLResponse)
async def cliente_chat_detail(request: Request, conv_id: int, db: AsyncSession = Depends(get_db)):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")
    negocios_list = await cargar_negocios_db()
    negocios = {n["rut"]: n["nombre"] for n in negocios_list}

    result = await db.execute(
        select(Conversacion, Contacto)
        .join(Contacto, Conversacion.contacto_id == Contacto.id)
        .where(Conversacion.id == conv_id)
    )
    row = result.one_or_none()
    if not row:
        return HTMLResponse("Conversación no encontrada", status_code=404)

    conv, contacto = row
    if conv.negocio_rut != rut:
        return HTMLResponse("Acceso denegado", status_code=403)

    msgs_result = await db.execute(
        select(Mensaje).where(Mensaje.conversacion_id == conv.id).order_by(Mensaje.created_at)
    )
    mensajes = msgs_result.scalars().all()

    return templates.TemplateResponse(request, "cliente/conversacion_detail.html", {
        "conversacion": conv,
        "contacto_nombre": contacto.nombre or "",
        "contacto_telefono": contacto.telefono,
        "negocio_nombre": negocios.get(conv.negocio_rut, conv.negocio_rut),
        "mensajes": mensajes,
        **user_context(request),
        "pagina": "conversaciones",
    })


@router.get("/configuracion", response_class=HTMLResponse)
async def cliente_config(request: Request):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")
    negocios = await cargar_negocios_db()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)

    reglas = await cargar_reglas_negocio(rut)
    reglas_generales = await cargar_reglas_generales()
    numeros = await cargar_numeros_whatsapp(rut)

    return templates.TemplateResponse(request, "cliente/configuracion.html", {
        "negocio": negocio,
        "numeros": numeros,
        "reglas": reglas,
        "reglas_generales": reglas_generales,
        **user_context(request),
        "pagina": "configuracion",
    })


@router.post("/configuracion/reglas")
async def cliente_guardar_reglas(request: Request):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")

    form = await request.form()
    nuevo_texto = form.get("reglas", "").strip()

    await guardar_reglas_negocio(rut, nuevo_texto)
    return RedirectResponse(url="/cliente/configuracion", status_code=303)


@router.post("/configuracion/toggle")
async def cliente_toggle_bot(request: Request):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")

    negocios = await cargar_negocios_db()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)

    negocio["activo"] = not negocio.get("activo", True)
    await guardar_negocios_db(negocios)
    return RedirectResponse(url="/cliente/configuracion", status_code=303)


@router.get("/conexiones", response_class=HTMLResponse)
async def cliente_conexiones(request: Request):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")
    negocios = await cargar_negocios_db()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)

    numeros = await cargar_numeros_whatsapp(rut)
    tiene_personal = any(w["tipo_cuenta"] == "personal" for w in numeros)
    aviso = await obtener_aviso_cuenta_personal()
    aviso_visto = await aviso_personal_fue_visto(rut)

    return templates.TemplateResponse(request, "cliente/conexiones.html", {
        "negocio": negocio,
        "numeros": numeros,
        "tiene_personal": tiene_personal,
        "aviso_cuenta_personal": aviso,
        "aviso_visto": aviso_visto,
        **user_context(request),
        "pagina": "conexiones",
    })


@router.post("/conexiones/eliminar")
async def cliente_eliminar_numero(request: Request):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")

    form = await request.form()
    numero = form.get("numero", "").strip()
    if not numero:
        return RedirectResponse(url="/cliente/conexiones", status_code=303)

    numeros = await cargar_numeros_whatsapp(rut)
    if len(numeros) <= 1:
        return HTMLResponse("No puedes eliminar el único número activo", status_code=400)

    await eliminar_numero_whatsapp(rut, numero)
    return RedirectResponse(url="/cliente/conexiones", status_code=303)


@router.post("/conexiones/ignorar-aviso")
async def cliente_ignorar_aviso(request: Request):
    session = ensure_authenticated(request)
    if not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
    rut = session.get("negocio_rut", "")
    await marcar_aviso_personal_visto(rut)
    return RedirectResponse(url="/cliente/conexiones", status_code=303)
