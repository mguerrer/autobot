import pytest
from unittest.mock import patch, AsyncMock
from app.schemas import WebhookIn
from app.services.whatsapp_service import procesar_mensaje_entrante


class TestWebhookEndpoint:
    async def test_webhook_mensaje_valido(self, client, monkeypatch):
        mock = AsyncMock(return_value="Hola, bienvenido a Pizzería Napoli")
        monkeypatch.setattr("app.services.whatsapp_service.generar_respuesta", mock)

        response = await client.post("/webhook/whatsapp", json={
            "bot_whatsapp": "+56998765432",
            "from_number": "+56911111111",
            "message": "Hola, ¿cuánto cuesta una pizza?",
            "message_id": "msg_001",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_webhook_mensaje_vacio(self, client):
        response = await client.post("/webhook/whatsapp", json={
            "bot_whatsapp": "+56998765432",
            "from_number": "+56911111111",
            "message": "",
            "message_id": "",
        })
        assert response.status_code == 400

    async def test_webhook_verificacion_token_valido(self, client):
        response = await client.get(
            "/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=napoli_token_123&hub.challenge=1234567890"
        )
        assert response.status_code == 200
        assert response.text == "1234567890"

    async def test_webhook_verificacion_token_invalido(self, client):
        response = await client.get(
            "/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=token_invalido&hub.challenge=1234567890"
        )
        assert response.status_code == 403

    async def test_webhook_verificacion_sin_mode(self, client):
        response = await client.get(
            "/webhook/whatsapp?hub.verify_token=napoli_token_123&hub.challenge=1234567890"
        )
        assert response.status_code == 403

    async def test_webhook_bot_no_encontrado(self, client, monkeypatch):
        mock = AsyncMock(return_value="respuesta")
        monkeypatch.setattr("app.services.whatsapp_service.generar_respuesta", mock)

        response = await client.post("/webhook/whatsapp", json={
            "bot_whatsapp": "+99999999999",
            "from_number": "+56911111111",
            "message": "Hola",
            "message_id": "msg_002",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_webhook_invalido_sin_campos(self, client):
        response = await client.post("/webhook/whatsapp", json={})
        assert response.status_code == 422


class TestProcesarMensaje:
    @patch("app.services.whatsapp_service.generar_respuesta", new_callable=AsyncMock)
    @patch("app.services.whatsapp_service.get_provider")
    async def test_procesar_y_responder(self, mock_provider, mock_ollama):
        mock_ollama.return_value = "Una pizza margherita cuesta $7.990"
        mock_provider.return_value.send_message = AsyncMock()

        await procesar_mensaje_entrante(
            bot_whatsapp="+56998765432",
            from_number="+56911111111",
            texto="¿Cuánto cuesta la pizza margherita?",
        )

        mock_ollama.assert_awaited_once()
        mock_provider.return_value.send_message.assert_awaited_once()

    @patch("app.services.whatsapp_service.generar_respuesta", new_callable=AsyncMock)
    @patch("app.services.whatsapp_service.get_provider")
    async def test_historial_se_mantiene(self, mock_provider, mock_ollama):
        mock_ollama.return_value = "Respuesta de prueba"
        mock_provider.return_value.send_message = AsyncMock()

        await procesar_mensaje_entrante(
            bot_whatsapp="+56998765432",
            from_number="+56911111111",
            texto="Mensaje 1",
        )

        await procesar_mensaje_entrante(
            bot_whatsapp="+56998765432",
            from_number="+56911111111",
            texto="Mensaje 2",
        )

        assert mock_ollama.await_count == 2
        assert mock_provider.return_value.send_message.await_count == 2
