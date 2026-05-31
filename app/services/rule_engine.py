import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATOS_DIR = BASE_DIR / "datos"


def cargar_reglas_generales() -> str:
    ruta = DATOS_DIR / "reglas_generales.md"
    if not ruta.exists():
        return ""
    return ruta.read_text(encoding="utf-8")


def cargar_reglas_negocio(rut: str) -> str:
    ruta = DATOS_DIR / "reglas_negocio.md"
    if not ruta.exists():
        return ""
    contenido = ruta.read_text(encoding="utf-8")
    patron = rf"## negocio:\s*{re.escape(rut)}\s*\n(.*?)(?=\n## negocio:|\Z)"
    match = re.search(patron, contenido, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def cargar_negocios() -> list[dict]:
    import json
    ruta = DATOS_DIR / "negocios.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def cargar_rubros() -> list[dict]:
    import json
    ruta = DATOS_DIR / "rubros.json"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def buscar_negocio_por_whatsapp(bot_whatsapp: str) -> dict | None:
    negocios = cargar_negocios()
    for n in negocios:
        if n.get("bot_whatsapp") == bot_whatsapp and n.get("activo", False):
            return n
    return None


def construir_prompt_sistema(rut: str) -> str:
    generales = cargar_reglas_generales()
    especificas = cargar_reglas_negocio(rut)
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
