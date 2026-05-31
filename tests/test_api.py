import pytest


class TestAPINegocios:
    async def test_listar_negocios(self, client):
        response = await client.get("/api/negocios")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_negocio_tiene_campos_esperados(self, client):
        response = await client.get("/api/negocios")
        data = response.json()
        pizzeria = next(n for n in data if n["rut"] == "76.123.456-7")
        assert pizzeria["nombre"] == "Pizzería Napoli"
        assert pizzeria["rubro_nombre"] == "Restaurante"
        assert pizzeria["activo"] is True
        assert pizzeria["bot_whatsapp"] == "+56998765432"


class TestAPIConversaciones:
    async def test_conversaciones_vacio_sin_datos(self, client):
        response = await client.get("/api/conversaciones")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_conversaciones_filtro_negocio(self, client):
        response = await client.get("/api/conversaciones?negocio_rut=76.123.456-7")
        assert response.status_code == 200

    async def test_mensajes_conversacion_inexistente(self, client):
        response = await client.get("/api/conversaciones/99999/mensajes")
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestAdmin:
    async def test_dashboard_carga(self, client):
        response = await client.get("/admin/")
        assert response.status_code == 200
        assert "Autobot" in response.text

    async def test_pagina_negocios(self, client):
        response = await client.get("/admin/negocios")
        assert response.status_code == 200
        assert "Negocios" in response.text
        assert "Pizzería Napoli" in response.text

    async def test_detalle_negocio(self, client):
        response = await client.get("/admin/negocios/76.123.456-7")
        assert response.status_code == 200
        assert "Pizzería Napoli" in response.text
        assert "+56998765432" in response.text

    async def test_detalle_negocio_no_existe(self, client):
        response = await client.get("/admin/negocios/00.000.000-0")
        assert response.status_code == 404

    async def test_chats_sin_conversaciones(self, client):
        response = await client.get("/admin/chats")
        assert response.status_code == 200
        assert "Conversaciones" in response.text


class TestRedireccion:
    async def test_root_redirige_a_admin(self, client):
        response = await client.get("/", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "/admin/" in response.headers.get("location", "")
