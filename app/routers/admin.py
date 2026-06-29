import httpx
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Conversacion, Contacto, Mensaje, Usuario
from app.services.rule_engine import (
    cargar_negocios_db, cargar_rubros, guardar_negocios_db,
    cargar_reglas_negocio, guardar_reglas_negocio,
    cargar_numeros_whatsapp, guardar_numero_whatsapp, eliminar_numero_whatsapp,
    obtener_aviso_cuenta_personal, guardar_aviso_cuenta_personal,
    exportar_negocios_json,
)
from app.auth import (
    get_session, create_session, hash_password, verify_password,
    ensure_authenticated, has_role, user_context,
)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
async def login_post(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")
    result = await db.execute(select(Usuario).where(Usuario.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "login.html", {"error": "Usuario o contraseña incorrectos"})
    token = create_session(user)
    response = RedirectResponse(url="/admin/", status_code=303)
    response.set_cookie(key="autobot_session", value=token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("autobot_session")
    return response


@router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request, db: AsyncSession = Depends(get_db)):
    session = ensure_authenticated(request)
    negocios = await cargar_negocios_db()
    rubros = {r["id"]: r["nombre"] for r in cargar_rubros()}

    if has_role(session, "cliente"):
        rut = session.get("negocio_rut", "")
        negocios = [n for n in negocios if n["rut"] == rut]

    result = await db.execute(select(Conversacion).order_by(desc(Conversacion.updated_at)).limit(10))
    conversaciones = result.scalars().all()

    convs = []
    for c in conversaciones:
        if has_role(session, "cliente") and c.negocio_rut != session.get("negocio_rut"):
            continue
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
        **user_context(request),
    })


@router.get("/negocios", response_class=HTMLResponse)
async def admin_negocios(request: Request):
    ensure_authenticated(request)
    negocios = await cargar_negocios_db()
    session = get_session(request)
    if has_role(session, "cliente"):
        rut = session.get("negocio_rut", "")
        negocios = [n for n in negocios if n["rut"] == rut]
    rubros = {rub["id"]: rub for rub in cargar_rubros()}
    return templates.TemplateResponse(request, "negocios.html", {
        "negocios": negocios,
        "rubros": rubros,
        **user_context(request),
    })


@router.get("/negocios/{rut}", response_class=HTMLResponse)
async def admin_negocio_detail(request: Request, rut: str, db: AsyncSession = Depends(get_db)):
    session = ensure_authenticated(request)
    if has_role(session, "cliente") and session.get("negocio_rut") != rut:
        return HTMLResponse("Acceso denegado", status_code=403)
    negocios = await cargar_negocios_db()
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
        **user_context(request),
    })


@router.get("/negocios/{rut}/editar", response_class=HTMLResponse)
async def admin_negocio_editar(request: Request, rut: str):
    session = ensure_authenticated(request)
    if has_role(session, "cliente") and session.get("negocio_rut") != rut:
        return HTMLResponse("Acceso denegado", status_code=403)
    negocios = await cargar_negocios_db()
    rubros = cargar_rubros()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)
    reglas_bot = await cargar_reglas_negocio(rut)
    return templates.TemplateResponse(request, "negocio_edit.html", {
        "negocio": negocio,
        "rubros": rubros,
        "reglas_bot": reglas_bot,
        **user_context(request),
    })


@router.post("/negocios/{rut}/editar")
async def admin_negocio_guardar(request: Request, rut: str):
    session = ensure_authenticated(request)
    if has_role(session, "cliente") and session.get("negocio_rut") != rut:
        return HTMLResponse("Acceso denegado", status_code=403)
    negocios = await cargar_negocios_db()
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

    await guardar_negocios_db(negocios)

    reglas_texto = form.get("reglas_bot", "").strip()
    await guardar_reglas_negocio(rut, reglas_texto)

    return RedirectResponse(url=f"/admin/negocios/{rut}", status_code=303)


@router.post("/negocios/{rut}/toggle")
async def admin_negocio_toggle(request: Request, rut: str):
    session = ensure_authenticated(request)
    if has_role(session, "cliente") and session.get("negocio_rut") != rut:
        return HTMLResponse("Acceso denegado", status_code=403)
    negocios = await cargar_negocios_db()
    negocio = next((n for n in negocios if n["rut"] == rut), None)
    if not negocio:
        return HTMLResponse("Negocio no encontrado", status_code=404)
    negocio["activo"] = not negocio["activo"]
    await guardar_negocios_db(negocios)
    return RedirectResponse(url="/admin/negocios", status_code=303)


@router.get("/chats", response_class=HTMLResponse)
async def admin_chats(request: Request, db: AsyncSession = Depends(get_db)):
    session = ensure_authenticated(request)
    negocios = {n["rut"]: n["nombre"] for n in await cargar_negocios_db()}
    stmt = (
        select(Conversacion, Contacto.telefono, Contacto.nombre)
        .join(Contacto, Conversacion.contacto_id == Contacto.id)
        .order_by(desc(Conversacion.updated_at))
    )
    if has_role(session, "cliente"):
        rut = session.get("negocio_rut", "")
        stmt = stmt.where(Conversacion.negocio_rut == rut)
    result = await db.execute(stmt)
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
        "ocultar_contenido": has_role(session, "admin"),
        **user_context(request),
    })


@router.get("/chats/{conv_id}", response_class=HTMLResponse)
async def admin_chat_detail(request: Request, conv_id: int, db: AsyncSession = Depends(get_db)):
    session = ensure_authenticated(request)
    negocios = {n["rut"]: n["nombre"] for n in await cargar_negocios_db()}

    result = await db.execute(
        select(Conversacion, Contacto)
        .join(Contacto, Conversacion.contacto_id == Contacto.id)
        .where(Conversacion.id == conv_id)
    )
    row = result.one_or_none()
    if not row:
        return HTMLResponse("Conversación no encontrada", status_code=404)

    conv, contacto = row

    if has_role(session, "cliente") and conv.negocio_rut != session.get("negocio_rut"):
        return HTMLResponse("Acceso denegado", status_code=403)

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
        "ocultar_contenido": has_role(session, "admin"),
        **user_context(request),
    })


@router.post("/chats/{conv_id}/responder")
async def admin_chat_responder(request: Request, conv_id: int, db: AsyncSession = Depends(get_db)):
    session = ensure_authenticated(request)
    if has_role(session, "admin", "ventas"):
        return HTMLResponse("Solo el dueño del negocio puede responder conversaciones", status_code=403)
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

    if has_role(session, "cliente") and conv.negocio_rut != session.get("negocio_rut"):
        return HTMLResponse("Acceso denegado", status_code=403)

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


@router.get("/aviso-cuenta-personal", response_class=HTMLResponse)
async def admin_aviso_cuenta_personal(request: Request):
    session = ensure_authenticated(request)
    aviso = await obtener_aviso_cuenta_personal()
    return templates.TemplateResponse(request, "admin/aviso_cuenta_personal.html", {
        "aviso": aviso,
        **user_context(request),
    })


@router.post("/aviso-cuenta-personal")
async def admin_guardar_aviso_cuenta_personal(request: Request):
    session = ensure_authenticated(request)
    form = await request.form()
    texto = form.get("aviso", "").strip()
    await guardar_aviso_cuenta_personal(texto)
    return RedirectResponse(url="/admin/aviso-cuenta-personal", status_code=303)


async def _numeros_del_cliente(rut: str) -> set[str]:
    nums = await cargar_numeros_whatsapp(rut)
    return {n["numero"] for n in nums}


@router.get("/wa-bridge", response_class=HTMLResponse)
async def admin_wa_bridge(request: Request):
    session = ensure_authenticated(request)
    es_admin = has_role(session, "admin", "ventas")
    if not es_admin and not has_role(session, "cliente"):
        return HTMLResponse("Acceso denegado", status_code=403)
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

        if not es_admin:
            numeros_cliente = await _numeros_del_cliente(session.get("negocio_rut", ""))
            sessions_data = [s for s in sessions_data if s.get("numero") in numeros_cliente]

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
        **user_context(request),
    })


async def _verificar_numero_permiso(session: dict, numero: str) -> str | None:
    if has_role(session, "admin", "ventas"):
        return None
    if has_role(session, "cliente"):
        rut = session.get("negocio_rut", "")
        nums = await _numeros_del_cliente(rut)
        if numero in nums:
            return None
        return "No tienes permiso para controlar este número"
    return "Acceso denegado"


@router.post("/wa-bridge/{numero}/start")
async def admin_wa_bridge_start(request: Request, numero: str):
    session = ensure_authenticated(request)
    err = await _verificar_numero_permiso(session, numero)
    if err:
        return JSONResponse({"error": err}, status_code=403)
    await exportar_negocios_json()
    bridge_url = settings.wa_bridge_url
    if not bridge_url:
        return JSONResponse({"error": "WA_BRIDGE_URL no configurado"}, status_code=400)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{bridge_url}/session/{numero}/start")
    return JSONResponse(resp.json(), status_code=resp.status_code)


@router.post("/wa-bridge/{numero}/stop")
async def admin_wa_bridge_stop(request: Request, numero: str):
    session = ensure_authenticated(request)
    err = await _verificar_numero_permiso(session, numero)
    if err:
        return JSONResponse({"error": err}, status_code=403)
    bridge_url = settings.wa_bridge_url
    if not bridge_url:
        return JSONResponse({"error": "WA_BRIDGE_URL no configurado"}, status_code=400)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{bridge_url}/session/{numero}/stop")
    return JSONResponse(resp.json(), status_code=resp.status_code)


@router.post("/wa-bridge/{numero}/restart")
async def admin_wa_bridge_restart(request: Request, numero: str):
    session = ensure_authenticated(request)
    err = await _verificar_numero_permiso(session, numero)
    if err:
        return JSONResponse({"error": err}, status_code=403)
    await exportar_negocios_json()
    bridge_url = settings.wa_bridge_url
    if not bridge_url:
        return JSONResponse({"error": "WA_BRIDGE_URL no configurado"}, status_code=400)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{bridge_url}/session/{numero}/restart")
    return JSONResponse(resp.json(), status_code=resp.status_code)
