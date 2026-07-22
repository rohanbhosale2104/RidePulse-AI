"""
FastAPI application entrypoint.

Wires together: MongoDB (Motor) lifecycle, ML model loading, JWT-secured
API routes, and Jinja2-rendered HTML pages for the dashboard/login/predict UI.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.connection import mongo_manager
from app.ml.predictor import ModelBundle
from app.routes import analytics_routes, auth_routes, predict_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

BASE_DIR = os.path.dirname(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    await mongo_manager.connect()
    try:
        ModelBundle.instance().load(settings.MODEL_PATH)
    except FileNotFoundError:
        logger.warning(
            "Starting server WITHOUT a loaded model. Predictions will fail "
            "until 'trained_models/uber_demand_model.joblib' is present."
        )
    yield
    # --- Shutdown ---
    await mongo_manager.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static & templates ---
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- API routers ---
app.include_router(auth_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(predict_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_routes.router, prefix=settings.API_V1_PREFIX)


# ---------------------------------------------------------------------------
# HTML page routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/predict", response_class=HTMLResponse, include_in_schema=False)
async def predict_page(request: Request):
    return templates.TemplateResponse("predict.html", {"request": request})


@app.get("/health", include_in_schema=False)
async def health():
    return {
        "status": "ok",
        "model_loaded": ModelBundle.instance().is_ready(),
    }
