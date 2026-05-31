import pytest
from sqlalchemy import select
from app.models import Contacto, Conversacion, Mensaje


class TestContacto:
    async def test_crear_contacto(self, db_session):
        c = Contacto(telefono="+56912345678", negocio_rut="76.123.456-7")
        db_session.add(c)
        await db_session.commit()
        await db_session.refresh(c)
        assert c.id is not None
        assert c.telefono == "+56912345678"

    async def test_contacto_con_nombre(self, db_session):
        c = Contacto(telefono="+56987654321", negocio_rut="77.789.012-3", nombre="Juan Pérez")
        db_session.add(c)
        await db_session.commit()
        await db_session.refresh(c)
        assert c.nombre == "Juan Pérez"


class TestConversacion:
    async def test_crear_conversacion(self, db_session):
        c = Contacto(telefono="+56912345678", negocio_rut="76.123.456-7")
        db_session.add(c)
        await db_session.commit()
        await db_session.refresh(c)

        conv = Conversacion(contacto_id=c.id, negocio_rut="76.123.456-7")
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)
        assert conv.id is not None
        assert conv.estado == "activa"


class TestMensaje:
    async def test_crear_mensaje(self, db_session):
        c = Contacto(telefono="+56912345678", negocio_rut="76.123.456-7")
        db_session.add(c)
        await db_session.commit()
        await db_session.refresh(c)

        conv = Conversacion(contacto_id=c.id, negocio_rut="76.123.456-7")
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)

        msg = Mensaje(conversacion_id=conv.id, rol="user", contenido="Hola")
        db_session.add(msg)
        await db_session.commit()
        await db_session.refresh(msg)
        assert msg.id is not None
        assert msg.rol == "user"
        assert msg.contenido == "Hola"

    async def test_mensajes_orden_cronologico(self, db_session):
        c = Contacto(telefono="+56912345678", negocio_rut="76.123.456-7")
        db_session.add(c)
        await db_session.commit()
        await db_session.refresh(c)

        conv = Conversacion(contacto_id=c.id, negocio_rut="76.123.456-7")
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)

        for i in range(3):
            db_session.add(Mensaje(conversacion_id=conv.id, rol="user", contenido=f"Mensaje {i}"))
        await db_session.commit()

        result = await db_session.execute(
            select(Mensaje).where(Mensaje.conversacion_id == conv.id).order_by(Mensaje.created_at)
        )
        msgs = result.scalars().all()
        assert len(msgs) == 3
        assert msgs[0].contenido == "Mensaje 0"
        assert msgs[2].contenido == "Mensaje 2"


class TestRelaciones:
    async def test_conversacion_tiene_mensajes(self, db_session):
        c = Contacto(telefono="+56912345678", negocio_rut="76.123.456-7")
        db_session.add(c)
        await db_session.commit()
        await db_session.refresh(c)

        conv = Conversacion(contacto_id=c.id, negocio_rut="76.123.456-7")
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)

        db_session.add(Mensaje(conversacion_id=conv.id, rol="user", contenido="Hola"))
        db_session.add(Mensaje(conversacion_id=conv.id, rol="assistant", contenido="Bienvenido"))
        await db_session.commit()

        from sqlalchemy.orm import selectinload
        result = await db_session.execute(
            select(Conversacion)
            .options(selectinload(Conversacion.mensajes))
            .where(Conversacion.id == conv.id)
        )
        conv_db = result.scalar_one()
        assert len(conv_db.mensajes) == 2
