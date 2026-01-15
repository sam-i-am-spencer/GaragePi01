"""
GaragePi - Raspberry Pi 5 Garage Door Controller

A FastAPI-based web application for controlling a garage door
via GPIO relay on a Raspberry Pi 5.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after logging is configured
from app.gpio_controller import init_controller, get_controller
from app.routers import garage

# API Key security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_settings():
    """Lazy load settings to allow app to start without .env for docs."""
    from app.config import settings
    return settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Initializes GPIO on startup and cleans up on shutdown.
    """
    # Startup
    logger.info("Starting GaragePi...")
    
    try:
        settings = get_settings()
        init_controller(
            chip_path=settings.gpio_chip,
            pin=settings.gpio_pin,
            active_high=settings.relay_active_high,
            pulse_duration_ms=settings.pulse_duration_ms
        )
        logger.info("GPIO controller initialized")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        # Allow app to start anyway for debugging
    
    yield
    
    # Shutdown
    logger.info("Shutting down GaragePi...")
    controller = get_controller()
    if controller:
        controller.cleanup()
    logger.info("Cleanup complete")


# Create FastAPI application
app = FastAPI(
    title="GaragePi",
    description="Raspberry Pi 5 Garage Door Controller API",
    version="1.0.0",
    lifespan=lifespan
)


async def verify_api_key(
    request: Request,
    api_key: str = Depends(API_KEY_HEADER)
):
    """
    Verify the API key for protected endpoints.
    
    Allows requests from the web UI (same origin) or with valid API key.
    """
    # Skip auth for static files and docs
    path = request.url.path
    if path in ["/", "/docs", "/redoc", "/openapi.json"] or path.startswith("/static"):
        return
    
    # Skip auth for health check
    if path == "/api/health":
        return
    
    # Check API key
    try:
        settings = get_settings()
        if api_key and api_key == settings.api_key:
            return
    except Exception:
        pass
    
    # Check for session cookie or referer from same origin (web UI)
    referer = request.headers.get("referer", "")
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    
    # Allow if request is from the same host (web UI)
    if host and (host in referer or host in origin):
        return
    
    # Also allow if it's a browser request with no API key header (web UI form)
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        return
    
    # For JSON requests, require API key
    if "application/json" in content_type or api_key == "":
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )


# Add API key verification to all routes
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Middleware to verify API key for protected endpoints."""
    path = request.url.path
    
    # Skip auth for static files, docs, health, and root
    if (path in ["/", "/docs", "/redoc", "/openapi.json", "/api/health"] 
        or path.startswith("/static")):
        return await call_next(request)
    
    # Check API key for API endpoints
    if path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key", "")
        
        try:
            settings = get_settings()
            valid_key = settings.api_key
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"detail": "Server configuration error"}
            )
        
        # Check referer/origin for web UI requests
        referer = request.headers.get("referer", "")
        host = request.headers.get("host", "")
        
        # Allow if valid API key or request from web UI
        if api_key == valid_key:
            return await call_next(request)
        
        if host and host in referer:
            return await call_next(request)
        
        # Reject unauthorized requests
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key. Use X-API-Key header."}
        )
    
    return await call_next(request)


# Include routers
app.include_router(garage.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "garagepi"}


# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Serve the web UI."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "GaragePi API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
