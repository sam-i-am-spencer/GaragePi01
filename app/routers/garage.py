"""API endpoints for garage door control."""

import time
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from app.gpio_controller import get_controller

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/garage", tags=["garage"])

# Simple rate limiting - track last trigger time
_last_trigger_time: float = 0
RATE_LIMIT_SECONDS = 2  # Minimum seconds between triggers


class TriggerResponse(BaseModel):
    """Response model for trigger endpoint."""
    success: bool
    message: str
    timestamp: str


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    status: str
    simulation_mode: bool
    gpio_pin: int
    timestamp: str


class DoorStatusResponse(BaseModel):
    """Response model for door sensor status endpoint."""
    door_state: str
    sensor_pin: int
    timestamp: str


def check_rate_limit():
    """Check if enough time has passed since last trigger."""
    global _last_trigger_time
    current_time = time.time()
    
    if current_time - _last_trigger_time < RATE_LIMIT_SECONDS:
        remaining = RATE_LIMIT_SECONDS - (current_time - _last_trigger_time)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited. Please wait {remaining:.1f} seconds."
        )
    
    _last_trigger_time = current_time


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_garage_door():
    """
    Trigger the garage door relay.
    
    Sends a pulse to the relay to simulate pressing the garage door button.
    Rate limited to prevent accidental rapid triggers.
    """
    # Check rate limit
    check_rate_limit()
    
    # Get GPIO controller
    controller = get_controller()
    if controller is None:
        raise HTTPException(
            status_code=500,
            detail="GPIO controller not initialized"
        )
    
    # Pulse the relay
    success = controller.pulse()
    
    if success:
        logger.info("Garage door triggered successfully")
        return TriggerResponse(
            success=True,
            message="Garage door triggered",
            timestamp=datetime.now().isoformat()
        )
    else:
        logger.error("Failed to trigger garage door")
        raise HTTPException(
            status_code=500,
            detail="Failed to trigger garage door relay"
        )


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get the current status of the garage controller.
    
    Returns information about the GPIO configuration and whether
    the system is running in simulation mode.
    """
    controller = get_controller()
    if controller is None:
        raise HTTPException(
            status_code=500,
            detail="GPIO controller not initialized"
        )
    
    return StatusResponse(
        status="ready",
        simulation_mode=controller._simulation_mode,
        gpio_pin=controller.pin,
        timestamp=datetime.now().isoformat()
    )


@router.get("/door-status", response_model=DoorStatusResponse)
async def get_door_status():
    """
    Get the current door sensor status.
    
    Returns the door state (OPEN, CLOSED, or UNKNOWN) based on
    the reed switch sensor reading.
    """
    controller = get_controller()
    if controller is None:
        raise HTTPException(
            status_code=500,
            detail="GPIO controller not initialized"
        )
    
    door_state = controller.read_door_sensor()
    
    return DoorStatusResponse(
        door_state=door_state,
        sensor_pin=controller.door_sensor_pin,
        timestamp=datetime.now().isoformat()
    )
