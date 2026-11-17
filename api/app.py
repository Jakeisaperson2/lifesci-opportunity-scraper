import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from api.routes.opportunities import router as opportunities_router
from api.routes.sources import router as sources_router
from api.routes.scrape import router as scrape_router
from api.routes.faculty import router as faculty_router
from api.routes.crm.organizations import router as orgs_router
from api.routes.crm.contacts import router as contacts_router
from api.routes.crm.activities import router as activities_router
from api.routes.crm.tasks import router as tasks_router
from api.routes.crm.pipeline import router as pipeline_router

app = FastAPI(
    title="LifeSci Opportunity Scraper",
    description="Business-development intelligence and CRM platform for academic medical centers.",
    version="2.0.0",
)

_base = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(_base / "frontend" / "static")), name="static")
templates = Jinja2Templates(directory=str(_base / "frontend" / "templates"))

app.include_router(opportunities_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(scrape_router, prefix="/api")
app.include_router(faculty_router, prefix="/api")
app.include_router(orgs_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok"}
