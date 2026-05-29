import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from api.routes.opportunities import router as opportunities_router
from api.routes.sources import router as sources_router
from api.routes.scrape import router as scrape_router

app = FastAPI(
    title="LifeSci Opportunity Discovery",
    description="Internal BD intelligence tool for discovering life sciences funding and collaboration opportunities.",
    version="0.1.0",
)

# Static files and templates
_base = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(_base / "frontend" / "static")), name="static")
templates = Jinja2Templates(directory=str(_base / "frontend" / "templates"))

# API routes
app.include_router(opportunities_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(scrape_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok"}
