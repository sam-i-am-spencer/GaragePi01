# 🏠 GaragePi

A Raspberry Pi 5 garage door controller with a mobile-friendly web interface.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Features

- **Mobile-Friendly Web UI** - Large button for easy garage door control from any device
- **Door Status Display** - Real-time open/closed status via reed switch sensor
- **REST API** - Integrate with Home Assistant, Apple Shortcuts, or custom automation
- **Docker Deployment** - Easy setup with Docker Compose
- **Secure** - API key authentication for external access
- **Rate Limited** - Prevents accidental rapid triggers
- **Pi 5 Compatible** - Uses modern `gpiod` library for GPIO control

## 🖥️ Screenshots

The web interface features a large, easy-to-tap button that works great on mobile devices.

## 🔧 Hardware Requirements

- Raspberry Pi 5 (running Ubuntu Server or Raspberry Pi OS)
- Relay module (configured for active HIGH)
- Reed switch sensor (magnetic door sensor) - optional but recommended
- Connection to your garage door opener button terminals

### Wiring

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

### Door Sensor Wiring (Optional)

```
Raspberry Pi 5          Reed Switch
─────────────────       ────────────
GPIO27 (Pin 13) ───────► Terminal 1
GND    (Pin 14) ───────► Terminal 2
```

> **Note:** Mount the reed switch on the garage door frame with the magnet on the door itself. When the door is closed, the magnet should be close to the sensor (circuit closed = LOW signal).

> **Note:** The relay simulates pressing the wall button. When triggered, it briefly closes the circuit (500ms pulse).

## 🚀 Quick Start

### Prerequisites

On your Raspberry Pi 5:
- Ubuntu Server or Raspberry Pi OS (64-bit recommended)
- Docker and Docker Compose installed
- Git installed

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sam-i-am-spencer/GaragePi01.git
   cd GaragePi01
   ```

2. **Create your environment file**
   ```bash
   cp .env.example .env
   ```

3. **Generate a secure API key and edit `.env`**
   ```bash
   # Generate a random API key
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Edit .env with your favorite editor
   nano .env
   ```

   Update the `API_KEY` value with your generated key:
   ```env
   API_KEY=your-generated-key-here
   ```

4. **Start the application**
   ```bash
   docker-compose up -d
   ```

5. **Access the web interface**
   
   Open your browser and go to:
   ```
   http://<raspberry-pi-ip>:8000
   ```

## 📖 Configuration

All configuration is done through the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | (required) | Secret key for API authentication |
| `GPIO_CHIP` | `/dev/gpiochip4` | GPIO chip device path (Pi 5 uses gpiochip4) |
| `GPIO_PIN` | `17` | GPIO pin number connected to relay |
| `RELAY_ACTIVE_HIGH` | `true` | Set to `false` if your relay activates on LOW |
| `DOOR_SENSOR_PIN` | `27` | GPIO pin for reed switch door sensor |
| `PULSE_DURATION_MS` | `500` | How long the relay stays on (milliseconds) |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

## 🔌 API Reference

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/` | No | Web UI |
| `GET` | `/api/health` | No | Health check |
| `GET` | `/api/garage/status` | Yes* | Controller status |
| `GET` | `/api/garage/door-status` | Yes* | Door sensor state (OPEN/CLOSED) |
| `POST` | `/api/garage/trigger` | Yes* | Trigger garage door |

*Authentication is automatically handled for requests from the web UI. External API calls require the `X-API-Key` header.

### Examples

**Trigger the garage door with curl:**
```bash
curl -X POST http://<pi-ip>:8000/api/garage/trigger \
  -H "X-API-Key: your-api-key"
```

**Check status:**
```bash
curl http://<pi-ip>:8000/api/garage/status \
  -H "X-API-Key: your-api-key"
```

**Check door sensor state:**
```bash
curl http://<pi-ip>:8000/api/garage/door-status \
  -H "X-API-Key: your-api-key"
# Returns: {"door_state": "OPEN" or "CLOSED", "sensor_pin": 27, "timestamp": "..."}
```

**Apple Shortcuts Integration:**
1. Create a new Shortcut
2. Add "Get Contents of URL" action
3. Set URL to `http://<pi-ip>:8000/api/garage/trigger`
4. Set Method to `POST`
5. Add Header: `X-API-Key` = your API key

## 🔄 Updating

To update to the latest version:

```bash
cd GaragePi01
git pull
docker-compose up -d --build
```

## 🐛 Troubleshooting

### Container won't start

Check the logs:
```bash
docker-compose logs -f
```

### GPIO permission denied

Ensure the GPIO device is accessible:
```bash
ls -la /dev/gpiochip*
```

If needed, add your user to the gpio group:
```bash
sudo usermod -aG gpio $USER
```

### Can't access web interface

1. Check if container is running:
   ```bash
   docker-compose ps
   ```

2. Check if port is open:
   ```bash
   curl http://localhost:8000/api/health
   ```

3. Check firewall (if applicable):
   ```bash
   sudo ufw allow 8000
   ```

### Test GPIO manually

Before using the app, verify GPIO works:
```bash
# Turn relay ON
gpioset /dev/gpiochip4 17=1

# Turn relay OFF  
gpioset /dev/gpiochip4 17=0
```

## 📁 Project Structure

```
garage_pi01/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── gpio_controller.py   # GPIO/relay control
│   └── routers/
│       └── garage.py        # API endpoints
├── static/
│   ├── index.html           # Web UI
│   ├── css/style.css        # Styling
│   └── js/app.js            # Frontend logic
├── .env.example             # Environment template
├── .gitignore
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container build
├── requirements.txt         # Python dependencies
└── README.md
```

## 🛡️ Security Considerations

- **API Key**: Keep your API key secret. Never commit `.env` to version control.
- **Local Network**: By default, this is designed for local network use only.
- **HTTPS**: For remote access, consider putting this behind a reverse proxy with SSL (e.g., Nginx, Traefik, or Cloudflare Tunnel).
- **Firewall**: Only expose port 8000 to trusted networks.

## 🔮 Future Enhancements

- [x] Door status sensor (magnetic reed switch) ✅
- [ ] Activity logging
- [ ] Multiple door support
- [ ] Home Assistant MQTT integration
- [ ] Push notifications

## 📄 License

MIT License - feel free to use and modify for your own projects.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [gpiod](https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/) - Linux GPIO library
