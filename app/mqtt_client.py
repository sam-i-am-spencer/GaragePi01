"""MQTT client for Home Assistant integration."""

import asyncio
import json
import logging
import threading

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.warning("paho-mqtt not available - MQTT disabled")


class GarageMQTT:
    """
    MQTT client for Home Assistant integration.

    Connects to an MQTT broker, publishes HA MQTT Discovery config,
    subscribes to command topics, and publishes door state changes.
    """

    def __init__(self, settings, controller):
        self.settings = settings
        self.controller = controller

        device_id = settings.mqtt_device_id
        prefix = settings.mqtt_discovery_prefix

        self.state_topic = f"{prefix}/cover/{device_id}/state"
        self.command_topic = f"{prefix}/cover/{device_id}/set"
        self.availability_topic = f"{prefix}/cover/{device_id}/availability"
        self.discovery_topic = f"{prefix}/cover/{device_id}/config"

        self._client = None
        self._connected = False

    def start(self):
        """Connect to the MQTT broker and start the network loop."""
        if not MQTT_AVAILABLE:
            logger.warning("paho-mqtt not installed, MQTT disabled")
            return

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"garagepi_{self.settings.mqtt_device_id}"
        )

        if self.settings.mqtt_username:
            self._client.username_pw_set(
                self.settings.mqtt_username,
                self.settings.mqtt_password
            )

        # Last Will: mark offline if we disconnect ungracefully
        self._client.will_set(
            self.availability_topic,
            payload="offline",
            retain=True
        )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        try:
            self._client.connect(
                self.settings.mqtt_host,
                self.settings.mqtt_port,
                keepalive=60
            )
            self._client.loop_start()
            logger.info(
                f"MQTT connecting to {self.settings.mqtt_host}:{self.settings.mqtt_port}"
            )
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")

    def stop(self):
        """Publish offline status and disconnect from the broker."""
        if self._client is None:
            return

        if self._connected:
            try:
                self._client.publish(self.availability_topic, "offline", retain=True)
            except Exception:
                pass

        self._client.loop_stop()
        try:
            self._client.disconnect()
        except Exception:
            pass
        logger.info("MQTT disconnected")

    def publish_state(self, state: str):
        """
        Publish the current door state.

        Thread-safe — can be called from any thread.
        Args:
            state: "open" or "closed"
        """
        if self._client is None or not self._connected:
            return
        try:
            self._client.publish(self.state_topic, state, retain=True)
            logger.debug(f"MQTT state published: {state}")
        except Exception as e:
            logger.error(f"Failed to publish MQTT state: {e}")

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        """Handle successful MQTT connection."""
        if reason_code.is_failure:
            logger.error(f"MQTT connection failed: {reason_code}")
            return

        self._connected = True
        logger.info("MQTT connected")

        # Publish HA discovery config
        client.publish(self.discovery_topic, self._discovery_payload(), retain=True)

        # Mark as online
        client.publish(self.availability_topic, "online", retain=True)

        # Subscribe to command topic
        client.subscribe(self.command_topic)
        logger.info(f"MQTT subscribed to {self.command_topic}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """Handle MQTT disconnection."""
        self._connected = False
        if reason_code.value != 0:
            logger.warning(f"MQTT disconnected unexpectedly: {reason_code}")
        else:
            logger.info("MQTT disconnected cleanly")

    def _on_message(self, client, userdata, message):
        """Handle incoming MQTT commands."""
        payload = message.payload.decode().strip()
        topic = message.topic

        if topic != self.command_topic:
            return

        if payload not in ("OPEN", "CLOSE", "STOP"):
            logger.warning(f"Ignoring unknown MQTT command: {payload!r}")
            return

        logger.info(f"MQTT command received: {payload}")
        # Run pulse in a thread so it doesn't block the paho network thread
        threading.Thread(target=self.controller.pulse, daemon=True).start()

    def _discovery_payload(self) -> str:
        """Build the Home Assistant MQTT Discovery JSON payload."""
        device_id = self.settings.mqtt_device_id
        payload = {
            "name": "Garage Door",
            "unique_id": f"{device_id}_cover",
            "device_class": "garage",
            "command_topic": self.command_topic,
            "state_topic": self.state_topic,
            "availability_topic": self.availability_topic,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "state_open": "open",
            "state_closed": "closed",
            "optimistic": False,
            "device": {
                "identifiers": [device_id],
                "name": "Garage Pi",
                "model": "Raspberry Pi 5",
                "manufacturer": "Custom",
            },
        }
        return json.dumps(payload)


async def door_monitor(mqtt_client: GarageMQTT, controller, interval: float = 0.5):
    """
    Monitor the door sensor and publish state changes via MQTT.

    Polls every `interval` seconds and publishes to MQTT when the state changes.
    """
    last_state = None

    while True:
        try:
            state = controller.read_door_sensor().lower()
            if state != last_state:
                logger.info(f"Door state changed: {last_state!r} -> {state!r}")
                last_state = state
                mqtt_client.publish_state(state)
        except Exception as e:
            logger.error(f"Door monitor error: {e}")

        await asyncio.sleep(interval)
