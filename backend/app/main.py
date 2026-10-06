"""FastAPI application entrypoint.

AI-Powered Intelligent Customer Support & Business Analytics Platform
ABC Financial Services Ltd. — Centium Technologies capstone reference build.

One process serves everything on one port:
  * /api/...   the REST API
  * /docs      interactive API documentation (Swagger)
  * /...       the React website (built into frontend/dist by start.sh)
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers import auth, tickets, assistant, analytics, admin
from app.seed import init_and_seed

settings = get_settings()

# Built website (npm run build). Override with STATIC_DIR if it lives elsewhere.
STATIC_DIR = Path(os.getenv(
    "STATIC_DIR",
    Path(__file__).resolve().parents[2] / "frontend" / "dist",
)).resolve()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables, train ML models, seed demo data, index the KB at startup.
    init_and_seed()
    if (STATIC_DIR / "index.html").is_file():
        print(f"[startup] website served from {STATIC_DIR}", flush=True)
    else:
        print(f"[startup] website not built yet ({STATIC_DIR} missing) - run ./start.sh", flush=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Reference implementation built from the capstone ERD, wireframes and SAD.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(assistant.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.app_name, "env": settings.env}


# ---------------------------------------------------------------------------
# Website: static assets + single-page-app fallback (must be registered last)
# ---------------------------------------------------------------------------
if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def website(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="Not Found")
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return JSONResponse(
            status_code=503,
            content={"detail": "The website has not been built yet. Run ./start.sh from the project folder."},
        )
    if full_path:
        candidate = (STATIC_DIR / full_path).resolve()
        if candidate.is_file() and STATIC_DIR in candidate.parents:
            return FileResponse(candidate)
    # Any other path (/, /login, /dashboard, ...) is a React route.
    return FileResponse(index)
