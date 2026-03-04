"""
GaragePi - Raspberry Pi 5 Garage Door Controller

FastAPI application for controlling a garage door via GPIO relay,
with Home Assistant MQTT integration.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
from app.mqtt_client import GarageMQTT, door_monitor

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_settings():
    """Lazy load settings to allow app to start without .env for docs."""
    from app.config import settings
    return settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize GPIO and MQTT on startup; clean up on shutdown."""
    logger.info("Starting GaragePi...")

    controller = None
    mqtt_client = None
    monitor_task = None

    try:
        settings = get_settings()
        controller = init_controller(
            chip_path=settings.gpio_chip,
            pin=settings.gpio_pin,
            active_high=settings.relay_active_high,
            pulse_duration_ms=settings.pulse_duration_ms,
            door_sensor_pin=settings.door_sensor_pin
        )
        logger.info("GPIO controller initialized")
    except Exception as e:
        logger.error(f"Failed to initialize GPIO: {e}")
        controller = get_controller()

    if controller is not None:
        try:
            settings = get_settings()
            mqtt_client = GarageMQTT(settings, controller)
            mqtt_client.start()
            monitor_task = asyncio.create_task(door_monitor(mqtt_client, controller))
            logger.info("MQTT client and door monitor started")
        except Exception as e:
            logger.error(f"Failed to start MQTT: {e}")

    yield

    # Shutdown
    logger.info("Shutting down GaragePi...")

    if monitor_task is not None:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

    if mqtt_client is not None:
        mqtt_client.stop()

    if controller is not None:
        controller.cleanup()

    logger.info("Cleanup complete")


# Create FastAPI application
app = FastAPI(
    title="GaragePi",
    description="Raspberry Pi 5 Garage Door Controller API",
    version="2.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Require X-API-Key for all /api/ endpoints except /api/health."""
    path = request.url.path

    # Always allow docs and health check
    if path in ["/docs", "/redoc", "/openapi.json", "/api/health"]:
        return await call_next(request)

    if path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key", "")

        try:
            settings = get_settings()
            if api_key == settings.api_key:
                return await call_next(request)
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"detail": "Server configuration error"}
            )

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


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
