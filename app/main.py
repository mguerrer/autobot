import logging
from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import init_db
from app.routers import admin, webhook, api, cliente
from app.auth import user_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando base de datos...")
    await init_db()
    logger.info("Autobot iniciado correctamente")
    yield
    logger.info("Autobot deteniéndose...")


app = FastAPI(title="Autobot", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(admin.router)
app.include_router(cliente.router)
app.include_router(webhook.router)
app.include_router(api.router)


@app.get("/qr-laura")
async def qr_laura():
    import base64
    from fastapi.responses import HTMLResponse
    png = Path("/tmp/qr_laura.png")
    html = Path("/tmp/qr_laura.html")
    if html.exists():
        content = html.read_text()
        return HTMLResponse(content)
    try:
        import urllib.request, json
        data = urllib.request.urlopen("http://localhost:9091/qr").read()
        d = json.loads(data)
        if d.get("qr"):
            return HTMLResponse(f'''<html><body style="display:flex;justify-content:center;align-items:center;height:100vh;background:#111"><img src="{d['qr']}" style="max-width:300px"></body></html>''')
    except:
        pass
    return HTMLResponse("<html><body><p>QR no disponible</p></body></html>")


@app.get("/ayuda", response_class=HTMLResponse)
async def pagina_ayuda(request: Request):
    return templates.TemplateResponse(request, "ayuda.html", {
        **user_context(request),
        "pagina": "ayuda",
    })


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/login")
