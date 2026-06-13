# Installation & Deployment Guide

## Übersicht

Dein Projekt ist komplett! Hier sind die nächsten Schritte:

```
📁 /home/seek/rpi-arc-middleware/
├── 📄 QUICKSTART.md          ← Start hier!
├── 📄 README.md              ← Detaillierte Doku
├── src/
│   ├── main.py               ← Entry point
│   ├── middleware.py         ← Koordinator
│   └── hardware/
│       ├── arc.py            ← Arc/serialosc
│       └── i2c_bus.py        ← i2c Devices
├── scripts/
│   ├── deploy.sh             ← Deploy Script
│   ├── setup-systemd.sh      ← Systemd Service
│   ├── test_basic.py         ← Local Tests
│   └── diagnose.py           ← Raspberry Pi Diagnostics
└── .vscode/
    ├── tasks.json            ← Deploy Tasks
    └── launch.json           ← Debugger Config
```

## Phase 1: Lokal testen

### 1. Test ohne Hardware

```bash
# Im Projekt Root:
python3 scripts/test_basic.py
```

Output sollte sein:
```
✓ All imports successful!
✓ ArcController works (mock)
✓ Middleware initialized successfully
```

### 2. Struktur verstehen

- Schau [README.md](README.md) für Code-Übersicht
- Beispiel: [src/examples/example_controller.py](src/examples/example_controller.py)

## Phase 2: Raspberry Pi vorbereiten

### 1. SSH-Zugang konfigurieren

```bash
# In VS Code: Cmd+Shift+P → "Install SSH Key"
# Oder manuell:
ssh-copy-id pi@monome-arc.local
```

Teste mit: Cmd+Shift+P → "Test SSH Connection"

### 2. Dependencies auf dem Pi installieren

```bash
ssh pi@monome-arc.local << 'EOF'
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev i2c-tools git

pip3 install python-osc smbus2 pyserial pyyaml

# Optional: USB Support
sudo apt-get install -y usbutils
EOF
```

### 3. Diagnostics auf dem Pi

```bash
ssh pi@monome-arc.local 'python3 /home/pi/arc-middleware/scripts/diagnose.py' \
  || echo "Deploy erst, dann diagnostics"
```

## Phase 3: Ersten Code deployen

### 1. Deploy & Start (einfachste Weise)

```bash
# Option A: VS Code Task (schnellste Weise)
# Cmd+Shift+P → "Deploy & Install"
# Dann: Cmd+Shift+P → "Start Service"

# Option B: Terminal
cd /home/seek/rpi-arc-middleware
./scripts/deploy.sh deploy
ssh pi@monome-arc.local 'cd /home/pi/arc-middleware && python3 src/main.py'

# Option C: Makefile
make deploy
make install  # auf Pi
make start    # auf Pi
```

### 2. Logs anschauen

```bash
# Cmd+Shift+P → "View Logs"
# Oder manuell:
ssh pi@monome-arc.local 'tail -f /home/pi/arc-middleware/logs/middleware.log'
```

## Phase 4: Deine Controller entwickeln

### Beispiel: Fader zu Arc

Bearbeite oder erstelle eine neue Datei in `src/`:

```python
from middleware import ArcMiddleware

# Konfiguration
config = {
    "arc_host": "127.0.0.1",
    "arc_port": 8000,
    "i2c_bus": 1,
}

middleware = ArcMiddleware(config)
arc = middleware.get_arc_controller()
faders = middleware.get_faders()

# Fader 0 → Arc Ring
def on_fader_0(value):
    brightness = value >> 12  # Skalierung
    arc.set_ring_led(ring=0, position=10, brightness=brightness)

faders.on_fader_change(0, on_fader_0)

middleware.start()
```

### Deploy & Test

1. Ändere Code
2. **Ctrl+Shift+B** (Deploy)
3. **Cmd+Shift+P** → "Start Service"
4. **Cmd+Shift+P** → "View Logs"

## Phase 5: Autostart (Optional)

Wenn du möchtest, dass die Middleware nach Reboot startet:

```bash
# Auf dem Pi:
ssh pi@monome-arc.local 'bash /home/pi/arc-middleware/scripts/setup-systemd.sh'

# Dann:
ssh pi@monome-arc.local 'sudo systemctl start arc-middleware'
ssh pi@monome-arc.local 'sudo systemctl status arc-middleware'
```

## Workflow-Zusammenfassung

### Edit → Deploy → Test Loop

1. **Bearbeite** `src/main.py` oder neue Module
2. **Ctrl+Shift+B** (Deploy via rsync)
3. **Cmd+Shift+P** → "Stop Service"
4. **Cmd+Shift+P** → "Start Service"
5. **Cmd+Shift+P** → "View Logs"
6. Zurück zu Punkt 1

### Tipps für schnelle Entwicklung

- **rsync ist schnell**: Nur geänderte Dateien werden transferiert
- **Logs live**: "View Logs" Task zeigt Output in Real-Time
- **Config.yaml**: Ändere `config.yaml`, deploy, kein Code-Rebuild nötig
- **Mehrere Sessions**: SSH + Terminal für Debugging

## Troubleshooting

### SSH funktioniert nicht
```bash
ping monome-arc.local
# Oder:
ssh pi@<pi-ip-address>
```

### i2c Geräte nicht sichtbar
```bash
ssh pi@monome-arc.local 'i2cdetect -y 1'
```

### serialosc nicht verbunden
- Arc muss per USB am Pi hängen
- `ssh pi@monome-arc.local 'lsusb'`

### Logs zeigen Fehler
```bash
# Full deployment mit debug:
./scripts/deploy.sh full
ssh pi@monome-arc.local 'python3 /home/pi/arc-middleware/src/main.py'
```

## Nächste Schritte

1. ✅ Lies [QUICKSTART.md](QUICKSTART.md)
2. ✅ Führe `python3 scripts/test_basic.py` aus
3. ✅ Deploy mit SSH Key setup
4. ✅ Teste mit `scripts/diagnose.py` auf dem Pi
5. ✅ Starte `make deploy && make start`
6. ✅ Schreibe deine erste Controller in `src/`

## Ressourcen

- [serialosc Documentation](https://monome.org/docs/serialosc/)
- [i2c Protokoll](https://en.wikipedia.org/wiki/I%C2%B2C)
- [Teletype i2c](https://github.com/monome/teletype)
- [16n Fader](https://github.com/16n-faderbank)

---

**Du bist ready! 🚀**

Fang mit `make deploy` an! 

Fragen? Schau die Logs oder nutze `scripts/diagnose.py` zur Fehlerbehebung.
