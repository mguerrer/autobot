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
    async def test_dashboard_carga(self, admin_client):
        response = await admin_client.get("/admin/")
        assert response.status_code == 200
        assert "Autobot" in response.text

    async def test_pagina_negocios(self, admin_client):
        response = await admin_client.get("/admin/negocios")
        assert response.status_code == 200
        assert "Negocios" in response.text
        assert "Pizzería Napoli" in response.text

    async def test_detalle_negocio(self, admin_client):
        response = await admin_client.get("/admin/negocios/76.123.456-7")
        assert response.status_code == 200
        assert "Pizzería Napoli" in response.text
        assert "+56998765432" in response.text

    async def test_detalle_negocio_no_existe(self, admin_client):
        response = await admin_client.get("/admin/negocios/00.000.000-0")
        assert response.status_code == 404

    async def test_chats_sin_conversaciones(self, admin_client):
        response = await admin_client.get("/admin/chats")
        assert response.status_code == 200
        assert "Conversaciones" in response.text


class TestAdminEditNegocio:
    async def test_edit_page_carga_con_reglas(self, admin_client):
        response = await admin_client.get("/admin/negocios/76.123.456-7/editar")
        assert response.status_code == 200
        assert "EasyMDE" in response.text
        assert "reglasEditor" in response.text
        assert "Pizzería Napoli" in response.text
        assert "$7.990" in response.text

    async def test_edit_page_negocio_inexistente(self, admin_client):
        response = await admin_client.get("/admin/negocios/00.000.000-0/editar")
        assert response.status_code == 404

    async def test_guardar_reglas_desde_admin(self, admin_client):
        nuevo_texto = "REGLAS TEST: atención personalizada 24/7"
        response = await admin_client.post(
            "/admin/negocios/76.123.456-7/editar",
            data={
                "nombre": "Pizzería Napoli",
                "dueno_nombre": "Carlos Pérez",
                "dueno_telefono": "+56911122333",
                "rubro_id": "1",
                "bot_whatsapp": "+56998765432",
                "reglas_bot": nuevo_texto,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = await admin_client.get("/admin/negocios/76.123.456-7/editar")
        assert nuevo_texto in response.text

    async def test_guardar_reglas_vacias(self, admin_client):
        response = await admin_client.post(
            "/admin/negocios/76.123.456-7/editar",
            data={
                "nombre": "Pizzería Napoli",
                "dueno_nombre": "Carlos Pérez",
                "dueno_telefono": "+56911122333",
                "rubro_id": "1",
                "bot_whatsapp": "+56998765432",
                "reglas_bot": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = await admin_client.get("/admin/negocios/76.123.456-7/editar")
        textarea = response.text.split("reglasEditor")[1].split(">", 1)[1].split("<")[0] if "reglasEditor" in response.text else ""
        assert textarea == ""

    async def test_cliente_edita_sus_reglas(self, cliente_client):
        response = await cliente_client.get("/admin/negocios/76.123.456-7/editar")
        assert response.status_code == 200
        assert "EasyMDE" in response.text

        nuevo = "CLIENTE TEST: reglas editadas por el dueño"
        response = await cliente_client.post(
            "/admin/negocios/76.123.456-7/editar",
            data={
                "nombre": "Pizzería Napoli",
                "dueno_nombre": "Carlos Pérez",
                "dueno_telefono": "+56911122333",
                "rubro_id": "1",
                "bot_whatsapp": "+56998765432",
                "reglas_bot": nuevo,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = await cliente_client.get("/admin/negocios/76.123.456-7/editar")
        assert nuevo in response.text

    async def test_cliente_no_edita_otro_negocio(self, cliente_client):
        response = await cliente_client.get("/admin/negocios/77.789.012-3/editar")
        assert response.status_code == 403


class TestRedireccion:
    async def test_root_redirige_a_admin(self, client):
        response = await client.get("/", follow_redirects=False)
        assert response.status_code in (302, 303, 307)
        assert "/admin/" in response.headers.get("location", "")

    async def test_admin_sin_auth_redirige(self, client):
        response = await client.get("/admin/negocios/76.123.456-7/editar", follow_redirects=False)
        assert response.status_code == 303
