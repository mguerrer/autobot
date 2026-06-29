import json
import re
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import ReglaGeneral, ReglaNegocio, Negocio, NumeroWhatsApp, Configuracion

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATOS_DIR = BASE_DIR / "datos"


async def cargar_reglas_generales() -> str:
    async with async_session() as db:
        result = await db.execute(select(ReglaGeneral).limit(1))
        row = result.scalar_one_or_none()
        return row.contenido if row else ""


async def guardar_reglas_generales(contenido: str) -> None:
    async with async_session() as db:
        result = await db.execute(select(ReglaGeneral).limit(1))
        row = result.scalar_one_or_none()
        if row:
            row.contenido = contenido
        else:
            db.add(ReglaGeneral(contenido=contenido))
        await db.commit()


async def cargar_reglas_negocio(rut: str) -> str:
    async with async_session() as db:
        result = await db.execute(
            select(ReglaNegocio).where(ReglaNegocio.negocio_rut == rut)
        )
        row = result.scalar_one_or_none()
        return row.contenido if row else ""


async def guardar_reglas_negocio(rut: str, contenido: str) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(ReglaNegocio).where(ReglaNegocio.negocio_rut == rut)
        )
        row = result.scalar_one_or_none()
        if row:
            row.contenido = contenido
        else:
            db.add(ReglaNegocio(negocio_rut=rut, contenido=contenido))
        await db.commit()


async def cargar_negocios() -> list[dict]:
    return await cargar_negocios_db()


def cargar_rubros() -> list[dict]:
    ruta = DATOS_DIR / "rubros.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


async def guardar_negocios(negocios: list[dict]) -> None:
    await guardar_negocios_db(negocios)


async def buscar_negocio_por_whatsapp(bot_whatsapp: str) -> dict | None:
    return await buscar_negocio_por_whatsapp_db(bot_whatsapp)


async def cargar_negocios_db() -> list[dict]:
    negocios = []
    async with async_session() as db:
        result = await db.execute(select(Negocio))
        for n in result.scalars().all():
            numeros_result = await db.execute(
                select(NumeroWhatsApp).where(NumeroWhatsApp.negocio_rut == n.rut)
            )
            nums = numeros_result.scalars().all()
            entry = {
                "id": n.id,
                "rut": n.rut,
                "nombre": n.nombre,
                "rubro_id": n.rubro_id,
                "dueno_nombre": n.dueno_nombre,
                "dueno_telefono": n.dueno_telefono,
                "activo": n.activo,
                "numeros": [{"numero": w.numero, "tipo_cuenta": w.tipo_cuenta,
                             "phone_number_id": w.phone_number_id,
                             "verify_token": w.verify_token} for w in nums],
            }
            entry["bot_whatsapp"] = nums[0].numero if nums else ""
            entry["phone_number_id"] = nums[0].phone_number_id if nums else ""
            entry["verify_token"] = nums[0].verify_token if nums else ""
            negocios.append(entry)
    return negocios


async def guardar_negocios_db(negocios: list[dict]) -> None:
    async with async_session() as db:
        for nd in negocios:
            result = await db.execute(select(Negocio).where(Negocio.rut == nd["rut"]))
            n = result.scalar_one_or_none()
            if n:
                n.nombre = nd.get("nombre", n.nombre)
                n.rubro_id = nd.get("rubro_id", n.rubro_id)
                n.dueno_nombre = nd.get("dueno_nombre", n.dueno_nombre)
                n.dueno_telefono = nd.get("dueno_telefono", n.dueno_telefono)
                n.activo = nd.get("activo", n.activo)
            else:
                n = Negocio(
                    rut=nd["rut"],
                    nombre=nd.get("nombre", ""),
                    rubro_id=nd.get("rubro_id", 0),
                    dueno_nombre=nd.get("dueno_nombre", ""),
                    dueno_telefono=nd.get("dueno_telefono", ""),
                    activo=nd.get("activo", True),
                )
                db.add(n)
            await db.flush()

            bot = nd.get("bot_whatsapp", "")
            if bot:
                exist = await db.execute(
                    select(NumeroWhatsApp).where(
                        NumeroWhatsApp.negocio_rut == nd["rut"],
                        NumeroWhatsApp.numero == bot,
                    )
                )
                if not exist.scalar_one_or_none():
                    db.add(NumeroWhatsApp(
                        negocio_rut=nd["rut"],
                        numero=bot,
                        tipo_cuenta="personal",
                        phone_number_id=nd.get("phone_number_id", ""),
                        verify_token=nd.get("verify_token", ""),
                    ))
        await db.commit()
    await exportar_negocios_json()


async def cargar_numeros_whatsapp(rut: str) -> list[dict]:
    numeros = []
    async with async_session() as db:
        result = await db.execute(
            select(NumeroWhatsApp).where(NumeroWhatsApp.negocio_rut == rut)
        )
        for w in result.scalars().all():
            numeros.append({
                "id": w.id,
                "numero": w.numero,
                "tipo_cuenta": w.tipo_cuenta,
                "phone_number_id": w.phone_number_id,
                "verify_token": w.verify_token,
                "activo": w.activo,
            })
    return numeros


async def guardar_numero_whatsapp(rut: str, numero: str, tipo_cuenta: str = "personal",
                                   phone_number_id: str = "", verify_token: str = "") -> None:
    async with async_session() as db:
        result = await db.execute(
            select(NumeroWhatsApp).where(
                NumeroWhatsApp.negocio_rut == rut,
                NumeroWhatsApp.numero == numero,
            )
        )
        w = result.scalar_one_or_none()
        if w:
            w.tipo_cuenta = tipo_cuenta
            w.phone_number_id = phone_number_id
            w.verify_token = verify_token
        else:
            db.add(NumeroWhatsApp(
                negocio_rut=rut,
                numero=numero,
                tipo_cuenta=tipo_cuenta,
                phone_number_id=phone_number_id,
                verify_token=verify_token,
            ))
        await db.commit()
    await exportar_negocios_json()


async def eliminar_numero_whatsapp(rut: str, numero: str) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(NumeroWhatsApp).where(
                NumeroWhatsApp.negocio_rut == rut,
                NumeroWhatsApp.numero == numero,
            )
        )
        w = result.scalar_one_or_none()
        if w:
            await db.delete(w)
            await db.commit()
    await exportar_negocios_json()


async def buscar_negocio_por_whatsapp_db(bot_whatsapp: str) -> dict | None:
    async with async_session() as db:
        result = await db.execute(
            select(NumeroWhatsApp).where(
                NumeroWhatsApp.numero == bot_whatsapp,
                NumeroWhatsApp.activo == True,
            )
        )
        w = result.scalar_one_or_none()
        if not w:
            return None
        neg_result = await db.execute(select(Negocio).where(Negocio.rut == w.negocio_rut))
        n = neg_result.scalar_one_or_none()
        if not n or not n.activo:
            return None
        return {
            "rut": n.rut,
            "nombre": n.nombre,
            "rubro_id": n.rubro_id,
            "dueno_nombre": n.dueno_nombre,
            "dueno_telefono": n.dueno_telefono,
            "bot_whatsapp": w.numero,
            "phone_number_id": w.phone_number_id,
            "verify_token": w.verify_token,
            "activo": n.activo,
        }


async def obtener_aviso_cuenta_personal() -> str:
    async with async_session() as db:
        result = await db.execute(
            select(Configuracion).where(Configuracion.clave == "aviso_cuenta_personal")
        )
        row = result.scalar_one_or_none()
        if row:
            return row.valor
    return (
        "⚠️ Aviso importante: cuentas personales de WhatsApp\n\n"
        "Has configurado uno o más números como cuenta personal. "
        "Esto significa que el bot usará WhatsApp Web (Baileys) para enviar y recibir mensajes.\n\n"
        "Ten en cuenta:\n"
        "• Meta no permite usar cuentas personales para fines automatizados o comerciales "
        "(viola sus términos de servicio).\n"
        "• Si Meta detecta actividad automatizada, puede suspender o bloquear permanentemente "
        "tu número de WhatsApp.\n"
        "• Para evitar riesgos, usa una cuenta de negocio oficial (Meta Cloud API) "
        "diseñada para este propósito.\n\n"
        "Consulta con tu administrador si tienes dudas."
    )


async def guardar_aviso_cuenta_personal(texto: str) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(Configuracion).where(Configuracion.clave == "aviso_cuenta_personal")
        )
        row = result.scalar_one_or_none()
        if row:
            row.valor = texto
        else:
            db.add(Configuracion(clave="aviso_cuenta_personal", valor=texto))
        await db.commit()


async def marcar_aviso_personal_visto(rut: str) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(Configuracion).where(Configuracion.clave == f"aviso_ignorado_{rut}")
        )
        if not result.scalar_one_or_none():
            db.add(Configuracion(clave=f"aviso_ignorado_{rut}", valor="1"))
            await db.commit()


async def aviso_personal_fue_visto(rut: str) -> bool:
    async with async_session() as db:
        result = await db.execute(
            select(Configuracion).where(Configuracion.clave == f"aviso_ignorado_{rut}")
        )
        return result.scalar_one_or_none() is not None


async def construir_prompt_sistema(rut: str) -> str:
    generales = await cargar_reglas_generales()
    especificas = await cargar_reglas_negocio(rut)
    negocio = None
    for n in await cargar_negocios_db():
        if n.get("rut") == rut:
            negocio = n
            break
    rubros = cargar_rubros()
    rubro_nombre = ""
    if negocio:
        for r in rubros:
            if r.get("id") == negocio.get("rubro_id"):
                rubro_nombre = r["nombre"]
                break

    partes = [
        "Eres un bot de atención al cliente automatizado.",
        f"Negocio: {negocio['nombre'] if negocio else 'Desconocido'} (RUT: {rut})",
        f"Rubro: {rubro_nombre}",
        "",
        "=== REGLAS GENERALES ===",
        generales,
    ]
    if especificas:
        partes.extend(["", "=== REGLAS ESPECÍFICAS DEL NEGOCIO ===", especificas])

    partes.extend([
        "",
        "Instrucciones adicionales:",
        "- Responde de forma natural y conversacional.",
        "- No menciones que eres una IA ni que usas reglas.",
        "- Usa la información del negocio para responder preguntas sobre productos, precios y horarios.",
        "- Si te preguntan algo fuera del contexto del negocio, responde amablemente que solo puedes ayudar con consultas relacionadas.",
    ])

    return "\n".join(partes)


async def exportar_negocios_json() -> None:
    ruta = DATOS_DIR / "negocios.json"
    negocios = await cargar_negocios_db()
    ruta.write_text(json.dumps(negocios, ensure_ascii=False, indent=2), encoding="utf-8")


async def migrar_negocios_de_json_a_db() -> None:
    ruta_json = DATOS_DIR / "negocios.json"
    if not ruta_json.exists():
        return
    negocios = json.loads(ruta_json.read_text(encoding="utf-8"))
    async with async_session() as db:
        for nd in negocios:
            existing = await db.execute(select(Negocio).where(Negocio.rut == nd["rut"]))
            if existing.scalar_one_or_none():
                continue
            neg = Negocio(
                rut=nd["rut"],
                nombre=nd.get("nombre", ""),
                rubro_id=nd.get("rubro_id", 0),
                dueno_nombre=nd.get("dueno_nombre", ""),
                dueno_telefono=nd.get("dueno_telefono", ""),
                activo=nd.get("activo", True),
            )
            db.add(neg)
            await db.flush()

            num_existing = await db.execute(
                select(NumeroWhatsApp).where(
                    NumeroWhatsApp.negocio_rut == nd["rut"],
                    NumeroWhatsApp.numero == nd.get("bot_whatsapp", ""),
                )
            )
            if nd.get("bot_whatsapp") and not num_existing.scalar_one_or_none():
                db.add(NumeroWhatsApp(
                    negocio_rut=nd["rut"],
                    numero=nd["bot_whatsapp"],
                    tipo_cuenta="personal",
                    phone_number_id=nd.get("phone_number_id", ""),
                    verify_token=nd.get("verify_token", ""),
                ))
        await db.commit()


async def migrar_reglas_de_archivos_a_db() -> None:
    reglas_gral_path = DATOS_DIR / "reglas_generales.md"
    reglas_neg_path = DATOS_DIR / "reglas_negocio.md"

    async with async_session() as db:
        count = await db.execute(select(ReglaGeneral))
        if not count.scalar_one_or_none():
            if reglas_gral_path.exists():
                contenido = reglas_gral_path.read_text(encoding="utf-8")
                db.add(ReglaGeneral(contenido=contenido))
                await db.commit()

        if reglas_neg_path.exists():
            contenido = reglas_neg_path.read_text(encoding="utf-8")
            patron = r"## negocio:\s*([^\n]+)\s*\n(.*?)(?=\n## negocio:|\Z)"
            for match in re.finditer(patron, contenido, re.DOTALL):
                rut = match.group(1).strip()
                texto = match.group(2).strip()
                existing = await db.execute(
                    select(ReglaNegocio).where(ReglaNegocio.negocio_rut == rut)
                )
                if not existing.scalar_one_or_none():
                    db.add(ReglaNegocio(negocio_rut=rut, contenido=texto))
            await db.commit()
