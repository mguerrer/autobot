import pytest
from app.services.rule_engine import (
    cargar_reglas_generales,
    cargar_reglas_negocio,
    cargar_negocios,
    cargar_rubros,
    buscar_negocio_por_whatsapp,
    construir_prompt_sistema,
)


pytestmark = pytest.mark.asyncio


class TestReglasGenerales:
    async def test_cargar_reglas_generales_no_vacio(self):
        contenido = await cargar_reglas_generales()
        assert contenido
        assert "Sé siempre amable" in contenido
        assert "Reglas Generales del Bot" in contenido

    async def test_reglas_incluyen_comportamiento_esperado(self):
        contenido = await cargar_reglas_generales()
        assert "Si no sabes la respuesta" in contenido
        assert "Mantén las respuestas concisas" in contenido


class TestReglasNegocio:
    async def test_cargar_reglas_pizzeria(self):
        reglas = await cargar_reglas_negocio("76.123.456-7")
        assert reglas
        assert "Pizzería Napoli" in reglas
        assert "$7.990" in reglas
        assert "Delivery gratis sobre $15.000" in reglas

    async def test_cargar_reglas_techsupport(self):
        reglas = await cargar_reglas_negocio("77.789.012-3")
        assert reglas
        assert "TechSupport Ltda." in reglas
        assert "Diagnóstico técnico" in reglas
        assert "Garantía de 3 meses" in reglas

    async def test_rut_inexistente_retorna_vacio(self):
        reglas = await cargar_reglas_negocio("00.000.000-0")
        assert reglas == ""


class TestRubros:
    def test_cargar_rubros(self):
        rubros = cargar_rubros()
        assert len(rubros) == 11
        nombres = [r["nombre"] for r in rubros]
        assert "Restaurante" in nombres
        assert "Tecnología" in nombres
        assert "Salud y Bienestar" in nombres

    def test_rubro_restaurante_id(self):
        rubros = cargar_rubros()
        rest = next(r for r in rubros if r["nombre"] == "Restaurante")
        assert rest["id"] == 1


class TestNegocios:
    def test_cargar_negocios(self):
        negocios = cargar_negocios()
        assert len(negocios) >= 3

    def test_pizzeria_napoli(self):
        negocios = cargar_negocios()
        pizzeria = next(n for n in negocios if n["rut"] == "76.123.456-7")
        assert pizzeria["nombre"] == "Pizzería Napoli"
        assert pizzeria["rubro_id"] == 1
        assert pizzeria["activo"] is True

    def test_techsupport(self):
        negocios = cargar_negocios()
        tech = next(n for n in negocios if n["rut"] == "77.789.012-3")
        assert tech["nombre"] == "TechSupport Ltda."
        assert tech["rubro_id"] == 7
        assert tech["dueno_nombre"] == "María Soto"


class TestBuscarNegocio:
    def test_buscar_por_whatsapp_existente(self):
        negocio = buscar_negocio_por_whatsapp("+56998765432")
        assert negocio is not None
        assert negocio["nombre"] == "Pizzería Napoli"

    def test_buscar_por_whatsapp_inexistente(self):
        negocio = buscar_negocio_por_whatsapp("+99999999999")
        assert negocio is None

    def test_buscar_negocio_inactivo(self):
        negocio = buscar_negocio_por_whatsapp("+56900000000")
        assert negocio is None

    def test_buscar_techsupport(self):
        negocio = buscar_negocio_por_whatsapp("+56987654321")
        assert negocio is not None
        assert negocio["rut"] == "77.789.012-3"


class TestPromptSistema:
    async def test_prompt_incluye_datos_negocio(self):
        prompt = await construir_prompt_sistema("76.123.456-7")
        assert "Pizzería Napoli" in prompt
        assert "Restaurante" in prompt

    async def test_prompt_incluye_reglas_generales(self):
        prompt = await construir_prompt_sistema("76.123.456-7")
        assert "Sé siempre amable" in prompt

    async def test_prompt_incluye_reglas_especificas(self):
        prompt = await construir_prompt_sistema("77.789.012-3")
        assert "TechSupport Ltda." in prompt
        assert "Diagnóstico técnico" in prompt

    async def test_prompt_incluye_instrucciones(self):
        prompt = await construir_prompt_sistema("76.123.456-7")
        assert "Eres un bot de atención al cliente" in prompt
        assert "No menciones que eres una IA" in prompt
