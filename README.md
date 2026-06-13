# Arc Cycles

Physics-based LED animations for the monome Arc on a Raspberry Pi A+. Six independent physics models (Cycles, Pendulum, Gravity, Spring, Orbit, Swing) can be assigned per ring — each of the four rings runs its own mode independently. A Monome Teletype can read state values and switch modes at runtime via an Arduino Nano V3.0 acting as an I2C bridge.

## Hardware

| Device | Connection | Address / Port |
|--------|-----------|----------------|
| Monome Arc (4 rings) | USB → serialosc | `/dev/ttyUSB0`, OSC port 14951 |
| Arduino Nano V3.0 | USB → `/dev/ttyUSB1` | I2C slave 0x31 (= 49 decimal) |
| Teletype I2C bus | A4/A5/GND on Nano | `IIA 49` |

4.7 kΩ pull-up resistors on SDA and SCL (to 3.3 V) are required.  
A bidirectional level shifter is used between the Arduino Nano V3.0 (5 V logic) and the Teletype I2C bus (3.3 V).

## Hardware Note

The physics parameters (sensitivity, impulse strength, friction) are tuned for the **DIY Arc by [theslowgrowth](https://github.com/theslowgrowth)**, which produces less encoder ticks per revolution than the original monome Arc. If you use an original Arc, you may need to change sensitivity values — for example `SENSITIVITY` and `IMPULSE` constants in the mode files under `src/apps/arc_cycles/modes/`.

## Physics Modes

| Nr | Name | Description |
|----|------|-------------|
| 1 | Cycles | Rotating dot with inertia and friction |
| 2 | Pendulum | Harmonic pendulum, 4 different periods |
| 3 | Gravity | Particles under gravity with bouncing |
| 4 | Spring | Spring mechanics with resonance effects |
| 5 | Orbit | Orbital model with multiple bodies per ring |
| 6 | Swing | Nonlinear pendulum (exact ODE, RK4 integration) |

Details: [docs/PHYSICS_MODES.md](docs/PHYSICS_MODES.md)

## Teletype Control

```
IIA 49       ; set I2C address (once)

; Switch all rings to the same mode
IIS 1        ; Cycles  IIS 2 Pendulum  IIS 3 Gravity
IIS 4        ; Spring  IIS 5 Orbit     IIS 6 Swing

; Switch a single ring — tens digit = ring (1–4), units = mode (1–6)
IIS 11       ; Ring 1 → Cycles      IIS 16  Ring 1 → Swing
IIS 26       ; Ring 2 → Swing       IIS 32  Ring 3 → Pendulum
IIS 43       ; Ring 4 → Gravity     (IIS 21–46 cover all combinations)

; Orientation
IIS 91       ; portrait (270°)      IIS 90  horizontal (default)
IIS 99       ; shut down Pi

; Read physics state per ring
IIQ 10       ; Ring 1 position  (0–5000)
IIQ 11       ; Ring 1 velocity  (±5000)
IIQ 12       ; Ring 1 angle     (±5000, Swing/Pendulum only)
IIQ 13       ; Ring 1 param1    (mode-specific)
; Rings 2–4: IIQ 2x / 3x / 4x
```

Each ring reports the state of whatever mode is currently running on it.  
Full reference: [docs/TELETYPE_REFERENCE.md](docs/TELETYPE_REFERENCE.md)

## Encoder Shortcuts

| Action | Effect |
|--------|--------|
| Turn encoder | Interact with physics (mode-dependent) |
| Press encoder | Reset that ring to initial state |
| Hold encoder 0 for > 2 s | Shut down Pi |

## Project Structure

```
src/
  arc_cycles_app.py          # entry point
  apps/arc_cycles/
    main.py                  # ArcCyclesApp (loop, mode management)
    mode_base.py             # base class, display routing
    modes/
      cycles_mode.py
      pendulum_mode.py
      gravity_mode.py
      spring_mode.py
      orbit_mode.py
      swing_mode.py
  hardware/
    arc.py                   # serialosc / OSC receiver
    arduino_serial.py        # Arduino serial bridge (IIS/IIQ)
arduino/
  teletype_bridge/           # Arduino firmware (I2C slave + serial)
scripts/
  deploy.sh                  # rsync deploy + service management
config.yaml                  # start mode, Arc address, Arduino port
```

## Setup

Full instructions: [QUICKSTART.md](QUICKSTART.md)

## License

MIT License — Copyright 2026 Doc Polyester.  
Third-party licenses: [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
