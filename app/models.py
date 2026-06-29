from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False, default="cliente")
    negocio_rut = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReglaGeneral(Base):
    __tablename__ = "reglas_generales"

    id = Column(Integer, primary_key=True)
    contenido = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ReglaNegocio(Base):
    __tablename__ = "reglas_negocio"

    id = Column(Integer, primary_key=True)
    negocio_rut = Column(String(20), unique=True, nullable=False, index=True)
    contenido = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Contacto(Base):
    __tablename__ = "contactos"

    id = Column(Integer, primary_key=True)
    telefono = Column(String(20), nullable=False, index=True)
    nombre = Column(String(100), default="")
    negocio_rut = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Conversacion(Base):
    __tablename__ = "conversaciones"

    id = Column(Integer, primary_key=True)
    contacto_id = Column(Integer, ForeignKey("contactos.id"), nullable=False)
    negocio_rut = Column(String(20), nullable=False, index=True)
    estado = Column(String(20), default="activa")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    contacto = relationship("Contacto")
    mensajes = relationship("Mensaje", back_populates="conversacion", order_by="Mensaje.created_at")


class Mensaje(Base):
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True)
    conversacion_id = Column(Integer, ForeignKey("conversaciones.id"), nullable=False)
    rol = Column(String(10), nullable=False)
    contenido = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversacion = relationship("Conversacion", back_populates="mensajes")
