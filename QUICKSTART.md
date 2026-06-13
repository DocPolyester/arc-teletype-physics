# Quick Start

## Prerequisites on the Raspberry Pi (once)

```bash
ssh seek@monome-arc.local

sudo apt-get update
sudo apt-get install python3 python3-pip serialosc

pip3 install python-osc pyserial pyyaml
```

`serialosc` must be running for the Arc to be detected. It typically starts automatically when the Arc is plugged in.

## Flash Arduino Firmware (once)

The firmware is in `arduino/teletype_bridge/teletype_bridge.ino`. Flash with the Arduino IDE or arduino-cli. On ARMv6 (Pi A+) use the system `avrdude`:

```bash
# From development machine with arduino-cli:
arduino-cli compile --fqbn arduino:avr:nano arduino/teletype_bridge/
arduino-cli upload  --fqbn arduino:avr:nano -p /dev/ttyUSB1 arduino/teletype_bridge/
```

## Deploy and Start

```bash
# From development machine:
./scripts/deploy.sh deploy && ./scripts/deploy.sh stop && ./scripts/deploy.sh start
```

The script deploys via `rsync` to `seek@monome-arc.local`.

## View Logs

```bash
ssh seek@monome-arc.local
tail -f /home/seek/arc-middleware/logs/arc_cycles.log
```

Or via VS Code task **"View Logs"**.

## Service Status

```bash
ssh seek@monome-arc.local systemctl status arc-cycles
```

## config.yaml

```yaml
default_mode: cycles        # cycles | pendulum | gravity | spring | orbit | swing

arc_host: "127.0.0.1"
arc_port: 14951
arc_prefix: "/monome"

arduino_serial:
  enabled: true
  port: "/dev/ttyUSB1"
  address: 0x31             # = 49 decimal (IIA 49 in Teletype)
```

## Teletype Setup

```
IIA 49       ; set I2C address (once per scene)
IIS 1        ; mode: Cycles
IIQ 10       ; read Ring 1 position (0–5000)
```

Full command reference: [docs/TELETYPE_REFERENCE.md](docs/TELETYPE_REFERENCE.md)

## Arc Encoder Shortcuts

| Action | Effect |
|--------|--------|
| Turn encoder | Interact with physics (mode-dependent) |
| Press encoder | Reset that ring |
| Press encoder 0 + 1 (within 2 s) | Shut down Pi |
