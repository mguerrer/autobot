import json
import re
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import ReglaGeneral, ReglaNegocio

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


def cargar_negocios() -> list[dict]:
    from app.services.rule_engine import DATOS_DIR
    ruta = DATOS_DIR / "negocios.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def cargar_rubros() -> list[dict]:
    ruta = DATOS_DIR / "rubros.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_negocios(negocios: list[dict]) -> None:
    ruta = DATOS_DIR / "negocios.json"
    ruta.write_text(
        json.dumps(negocios, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def buscar_negocio_por_whatsapp(bot_whatsapp: str) -> dict | None:
    negocios = cargar_negocios()
    for n in negocios:
        if n.get("bot_whatsapp") == bot_whatsapp and n.get("activo", False):
            return n
    return None


async def construir_prompt_sistema(rut: str) -> str:
    generales = await cargar_reglas_generales()
    especificas = await cargar_reglas_negocio(rut)
    negocio = None
    for n in cargar_negocios():
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
