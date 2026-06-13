# Teletype Command Reference — Arc Cycles

Communication between the Monome Teletype and the Raspberry Pi via an Arduino Nano V3.0 acting as an I2C slave bridge.

## Hardware Setup

```
Teletype I2C Bus
   SDA ─────────────┐
   SCL ─────────────┤──── Arduino Nano (A4=SDA, A5=SCL, GND)
   GND ─────────────┘         │ USB /dev/ttyUSB1
                           Raspberry Pi A+
```

4.7 kΩ pull-up resistors on SDA and SCL (to 3.3 V) are required.  
Arduino I2C address: **49 (decimal) = 0x31**

---

## Set Address (once per scene)

```
IIA 49
```

All subsequent `IIS` and `IIQ` commands target this address.

---

## IIS — Write Commands

Teletype writes **1 byte** to the Arduino. No `value` parameter needed — the command code itself is the value.

### Switch Mode — All Rings

| Command | Mode |
|---------|------|
| `IIS 1` | Cycles — rotating dot with inertia |
| `IIS 2` | Pendulum — harmonic pendulum |
| `IIS 3` | Gravity — gravity with bouncing |
| `IIS 4` | Spring — spring mechanics / resonance |
| `IIS 5` | Orbit — orbital model |
| `IIS 6` | Swing — nonlinear pendulum (RK4) |

### Switch Mode — Single Ring

Each ring can run a different mode independently.  
Command format: **tens digit = ring (1–4), units digit = mode (1–6)**

| Command | Ring | Mode |
|---------|------|------|
| `IIS 11` | Ring 1 | Cycles |
| `IIS 12` | Ring 1 | Pendulum |
| `IIS 13` | Ring 1 | Gravity |
| `IIS 14` | Ring 1 | Spring |
| `IIS 15` | Ring 1 | Orbit |
| `IIS 16` | Ring 1 | Swing |
| `IIS 21` | Ring 2 | Cycles |
| `IIS 22` | Ring 2 | Pendulum |
| … | … | … |
| `IIS 41` | Ring 4 | Cycles |
| … | … | … |
| `IIS 46` | Ring 4 | Swing |

### Arc Orientation

| Command | Effect |
|---------|--------|
| `IIS 90` | Horizontal — position 0 is on the left (default) |
| `IIS 91` | Portrait — position 0 is at the top (270°, 48 LEDs offset) |

### System

| Command | Effect |
|---------|--------|
| `IIS 99` | Shut down the Raspberry Pi immediately (`shutdown -h now`) |

---

## IIQ — Read Commands (Query)

Teletype writes a register code and reads back 2 bytes (int16, big-endian). Return range: **0–5000** (unsigned) or **−5000–+5000** (signed, depending on state).

Each ring reports the state of whatever mode is currently running on it.

### Register Scheme

```
Register = Ring × 10 + State
```

| Register | Ring | State |
|----------|------|-------|
| 10–13 | 0 (Ring 1) | 0–3 |
| 20–23 | 1 (Ring 2) | 0–3 |
| 30–33 | 2 (Ring 3) | 0–3 |
| 40–43 | 3 (Ring 4) | 0–3 |

### State Definitions

| State | Name | Description | Range |
|-------|------|-------------|-------|
| 0 | Position | Current LED position (0–63 → 0–5000) | 0 … 5000 |
| 1 | Velocity | Current speed / angular velocity | −5000 … +5000 |
| 2 | Angle | Angle (Swing and Pendulum only) | −5000 … +5000 |
| 3 | Param1 | Mode-specific parameter (see table below) | 0 … 5000 |

### Param1 (State 3) per Mode

| Mode | Param1 Content | Unit |
|------|----------------|------|
| Cycles | — (always 0) | — |
| Pendulum | Oscillation period | ms (1000–2500) |
| Gravity | Gravity strength × 500 | 0–5000 |
| Spring | Spring constant k × 1000 | 100–5000 |
| Orbit | Orbital period | ms (1000–2500) |
| Swing | Damping coefficient × 2500 | 0–5000 |

---

## Examples

```
; Set address once
IIA 49

; All rings → Swing mode
IIS 6

; Ring 1 → Cycles, Ring 2 → Swing, Ring 3 → Pendulum, Ring 4 → Gravity
IIS 11
IIS 26
IIS 32
IIS 43

; Read position of Ring 1 (state 0)
IIQ 10   ; returns 0–5000

; Read angular velocity of Ring 3 (state 1)
IIQ 31   ; returns −5000…+5000

; Read angle θ of Ring 2 (state 2, Swing / Pendulum only)
IIQ 22   ; returns −5000…+5000  (−π/2…+π/2 → −5000…+5000)

; Read oscillation period of Ring 4 (state 3, Pendulum mode)
IIQ 43   ; e.g. 2500 = 2.5 seconds

; Switch Ring 2 to Orbit mid-scene
IIS 25

; Switch to portrait orientation
IIS 91

; Shut down Pi
IIS 99
```

---

## Scene Example

```
; INIT
IIA 49
; Ring 1 Cycles, Ring 2 Swing, Ring 3 Swing (different length), Ring 4 Orbit
IIS 11
IIS 26
IIS 36
IIS 45

; METRO (e.g. every 250 ms)
X IIQ 10       ; position of Ring 1 (Cycles)
Y IIQ 21       ; velocity of Ring 2 (Swing)

; If Swing angle > 4000: switch Ring 2 to Spring
Z IIQ 22
IF GT Z 4000: IIS 24
```

---

## Notes

- The Arduino resets when the serial connection is opened (~2 s boot time). Queries during the first seconds after Pi startup may return 0.
- All values scale to **0–5000** (unsigned) or **±5000** (signed) for direct use as Teletype variables.
- IIQ always returns the state of whatever mode is active on that ring, even if rings are in different modes.
- Holding Encoder 0 (Ring 1 encoder) for more than 2 seconds shuts down the Pi — without Teletype.
- Per-ring mode can also be set in `config.yaml` under `ring_modes` for persistent startup configuration.
