from pydantic import BaseModel


class NegocioOut(BaseModel):
    rut: str
    nombre: str
    rubro_id: int
    rubro_nombre: str = ""
    dueno_nombre: str
    dueno_telefono: str
    bot_whatsapp: str
    activo: bool


class RubroOut(BaseModel):
    id: int
    nombre: str
    descripcion: str


class MensajeOut(BaseModel):
    id: int
    rol: str
    contenido: str
    created_at: str


class ConversacionOut(BaseModel):
    id: int
    contacto_telefono: str
    contacto_nombre: str
    negocio_rut: str
    negocio_nombre: str = ""
    estado: str
    ultimo_mensaje: str = ""
    updated_at: str


class WebhookIn(BaseModel):
    bot_whatsapp: str
    from_number: str
    message: str
    message_id: str = ""
