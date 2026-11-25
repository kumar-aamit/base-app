import logging
import re
from contextlib import asynccontextmanager
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from . import __version__
from .appspec import ICON_DIR, AppSpec, AppSpecError, load_app_spec
from .config import Settings
from .health import CheckResult, run_checks

HERE = Path(__file__).parent
log = logging.getLogger("baseapp")


@lru_cache(maxsize=None)
def _icon_svg(name: str) -> str:
    svg = (ICON_DIR / f"{name}.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
    return re.sub(r'class="[^"]*"', 'class="icon" aria-hidden="true"', svg, count=1)


def icon(name: str) -> Markup:
    return Markup(_icon_svg(name))


def create_app(settings: Settings) -> FastAPI:
    try:
        spec, config_error = load_app_spec(settings.app_dir), None
    except AppSpecError as exc:
        spec, config_error = AppSpec(), str(exc)
        log.error("%s", exc)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        client = getattr(app.state, "http", None)
        if client is not None:
            await client.aclose()

    app = FastAPI(title=spec.name, version=__version__, docs_url=None, redoc_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.globals["icon"] = icon

    def http_client() -> httpx.AsyncClient:
        if getattr(app.state, "http", None) is None:
            app.state.http = httpx.AsyncClient()
        return app.state.http

    def page_context() -> dict:
        return {
            "spec": spec,
            "site": spec.site or settings.site_name,
            "config_error": config_error,
            "commit": settings.commit,
            "platform_version": __version__,
        }

    @app.get("/health")
    @app.get("/healthz")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/version")
    async def version() -> dict:
        return {
            "commit": settings.commit,
            "platform": __version__,
            "app": spec.name,
            "config_error": config_error,
        }

    @app.get("/api/checks")
    async def checks(request: Request):
        rows = [CheckResult("App", True, f"running {settings.commit[:7]}", None)]
        rows += await run_checks(settings, http_client())
        if request.headers.get("hx-request"):
            return templates.TemplateResponse(request, "partials/checks.html", {"rows": rows})
        return [asdict(r) for r in rows]

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(request, "placeholder.html", page_context())

    return app


app = create_app(Settings.from_env())
