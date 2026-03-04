# GaragePi

A Raspberry Pi 5 garage door controller with Home Assistant integration via MQTT.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Home Assistant Integration** - Auto-discovered via MQTT Discovery as a garage door cover entity
- **Real-time Door State** - Reed switch sensor publishes open/closed state instantly via MQTT
- **REST API** - Control and monitor via HTTP for scripting or other integrations
- **Docker Deployment** - Easy setup with Docker Compose
- **Secure** - API key authentication for REST endpoints
- **Pi 5 Compatible** - Uses modern `gpiod` library for GPIO control

## Hardware Requirements

- Raspberry Pi 5 (running Ubuntu Server or Raspberry Pi OS)
- Relay module (configured for active HIGH)
- Reed switch sensor (magnetic door sensor)
- Connection to your garage door opener button terminals

### Relay Wiring

```
Raspberry Pi 5          Relay Module
─────────────────       ─────────────
GPIO17 (Pin 11) ───────► IN
5.0V   (Pin 2)  ───────► VCC
GND    (Pin 6)  ───────► GND

Relay Module            Garage Door Opener
─────────────           ──────────────────
COM ────────────────────► Button Terminal 1
NO  ────────────────────► Button Terminal 2
```

### Door Sensor Wiring

```
Raspberry Pi 5          Reed Switch
─────────────────       ────────────
GPIO27 (Pin 13) ───────► Terminal 1
GND    (Pin 14) ───────► Terminal 2
```

> **Note:** Mount the reed switch on the garage door frame with the magnet on the door itself. When the door is closed, the magnet should be close to the sensor (LOW signal = closed).

> **Note:** The relay simulates pressing the wall button — it briefly closes the circuit for 500ms.

## Quick Start

### Prerequisites

On your Raspberry Pi 5:
- Docker and Docker Compose installed
- Git installed
- An MQTT broker accessible on your network (e.g. the Mosquitto add-on in Home Assistant)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sam-i-am-spencer/GaragePi01.git
   cd GaragePi01
   ```

2. **Create your environment file**
   ```bash
   cp .env.example .env
   nano .env
   ```

3. **Generate a secure API key**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. **Configure `.env`** with your API key and MQTT broker details (see Configuration below)

5. **Start the application**
   ```bash
   docker compose up -d
   ```

6. **Check it's running**
   ```bash
   docker logs garagepi
   ```
   You should see `MQTT connected` and `MQTT subscribed to homeassistant/cover/garage_pi/set`.

### Home Assistant Setup

1. Install the **Mosquitto broker** add-on in Home Assistant
2. Go to **Settings → Devices & Services → Add Integration → MQTT**
3. Set broker to `localhost`, port `1883`, and enter your credentials
4. The **Garage Pi** device will appear automatically under **Settings → Devices & Services → MQTT** — no manual YAML required

## Configuration

All configuration is done through the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | (required) | Secret key for REST API authentication |
| `GPIO_CHIP` | `/dev/gpiochip4` | GPIO chip device path (Pi 5 uses gpiochip4) |
| `GPIO_PIN` | `17` | GPIO pin number connected to relay |
| `RELAY_ACTIVE_HIGH` | `true` | Set to `false` if your relay activates on LOW |
| `DOOR_SENSOR_PIN` | `27` | GPIO pin for reed switch door sensor |
| `PULSE_DURATION_MS` | `500` | How long the relay stays on (milliseconds) |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `MQTT_HOST` | `localhost` | MQTT broker hostname or IP |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` | | MQTT broker username |
| `MQTT_PASSWORD` | | MQTT broker password |
| `MQTT_DISCOVERY_PREFIX` | `homeassistant` | HA MQTT discovery prefix |
| `MQTT_DEVICE_ID` | `garage_pi` | Unique device ID used in MQTT topics |

### MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `homeassistant/cover/garage_pi/config` | Published | HA MQTT Discovery config |
| `homeassistant/cover/garage_pi/state` | Published | Door state (`open` / `closed`) |
| `homeassistant/cover/garage_pi/availability` | Published | `online` / `offline` |
| `homeassistant/cover/garage_pi/set` | Subscribed | Commands: `OPEN`, `CLOSE`, `STOP` |

## REST API

All endpoints except `/api/health` require the `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/garage/status` | Controller status |
| `GET` | `/api/garage/door-status` | Door sensor state |
| `POST` | `/api/garage/trigger` | Trigger garage door relay |

### Examples

```bash
# Trigger the garage door
curl -X POST http://<pi-ip>:8000/api/garage/trigger \
  -H "X-API-Key: your-api-key"

# Check door state
curl http://<pi-ip>:8000/api/garage/door-status \
  -H "X-API-Key: your-api-key"
```

## Updating

```bash
cd GaragePi01
git pull
docker compose up -d --build
```

## Troubleshooting

### Container won't start
```bash
docker logs garagepi
```

### MQTT not connecting

Check credentials in `.env` match your broker. Watch logs for `Not authorized` errors:
```bash
docker logs garagepi | grep MQTT
```

### GPIO permission denied
```bash
ls -la /dev/gpiochip*
```

### Test GPIO manually
```bash
# Turn relay ON
gpioset /dev/gpiochip4 17=1

# Turn relay OFF
gpioset /dev/gpiochip4 17=0
```

### Garage Pi device not appearing in Home Assistant

1. Confirm the MQTT integration is added in HA (Settings → Devices & Services → MQTT)
2. Use the **Listen to a topic** tool in the MQTT integration config and subscribe to `homeassistant/cover/garage_pi/#` — you should see `config`, `state`, and `availability` messages
3. Restart the container to force republishing: `docker compose restart`

## Project Structure

```
GaragePi01/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application & lifespan
│   ├── config.py            # Configuration management
│   ├── gpio_controller.py   # GPIO relay & sensor control
│   ├── mqtt_client.py       # Home Assistant MQTT integration
│   └── routers/
│       └── garage.py        # REST API endpoints
├── .env.example             # Environment template
├── .gitignore
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container build
├── requirements.txt         # Python dependencies
└── README.md
```

## Security Considerations

- **API Key**: Keep your API key secret. Never commit `.env` to version control.
- **Local Network**: Designed for local network use only.
- **HTTPS**: For remote access, put this behind a reverse proxy with SSL (e.g. Nginx, Traefik, or Cloudflare Tunnel).

## License

MIT License - feel free to use and modify for your own projects.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [gpiod](https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/) - Linux GPIO library
- [paho-mqtt](https://eclipse.dev/paho/index.php?page=clients/python/index.php) - MQTT client library
