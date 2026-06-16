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
| `IIS 1`  | Cycles — rotating dot with inertia |
| `IIS 2`  | Pendulum — harmonic pendulum |
| `IIS 3`  | Gravity — gravity with bouncing |
| `IIS 4`  | Spring — spring mechanics / resonance |
| `IIS 5`  | Orbit — orbital model |
| `IIS 6`  | Swing — nonlinear pendulum (RK4) |
| `IIS 7`  | Euclidean — Bjorklund rhythm sequencer |
| `IIS 8`  | Bounce — bouncing ball rhythm |
| `IIS 9`  | Drunk — Brownian motion walk |
| `IIS 50` | Chaos — Lorenz attractor |
| `IIS 51` | Probability — Bernoulli gate |

> **Note:** IIS 10 and 11 are avoided — they collide with IIQ register codes for Ring 1 (IIQ register 10 = position, 11 = velocity). IIS 50 and 51 are used instead for Chaos and Probability.

### Switch Mode — Single Ring

Each ring can run a different mode independently.

> **Note on numbering:** Teletype IIS sends a single byte (max 255). Rings 1 and 2 fit in `1xx` / `2xx` ranges. Rings 3 and 4 cannot use `3xx` / `4xx` (would exceed 255) — they use `221–231` and `241–251` instead.

**Ring 1 — IIS 101–111** (prefix `1xx`)

| Command | Mode |
|---------|------|
| `IIS 101` | Cycles |
| `IIS 102` | Pendulum |
| `IIS 103` | Gravity |
| `IIS 104` | Spring |
| `IIS 105` | Orbit |
| `IIS 106` | Swing |
| `IIS 107` | Euclidean |
| `IIS 108` | Bounce |
| `IIS 109` | Drunk |
| `IIS 110` | Chaos |
| `IIS 111` | Probability |

**Ring 2 — IIS 201–211** (prefix `2xx`)

| Command | Mode |
|---------|------|
| `IIS 201` | Cycles |
| `IIS 202` | Pendulum |
| `IIS 203` | Gravity |
| `IIS 204` | Spring |
| `IIS 205` | Orbit |
| `IIS 206` | Swing |
| `IIS 207` | Euclidean |
| `IIS 208` | Bounce |
| `IIS 209` | Drunk |
| `IIS 210` | Chaos |
| `IIS 211` | Probability |

**Ring 3 — IIS 221–231** (byte limit prevents `3xx`)

| Command | Mode |
|---------|------|
| `IIS 221` | Cycles |
| `IIS 222` | Pendulum |
| `IIS 223` | Gravity |
| `IIS 224` | Spring |
| `IIS 225` | Orbit |
| `IIS 226` | Swing |
| `IIS 227` | Euclidean |
| `IIS 228` | Bounce |
| `IIS 229` | Drunk |
| `IIS 230` | Chaos |
| `IIS 231` | Probability |

**Ring 4 — IIS 241–251** (byte limit prevents `4xx`)

| Command | Mode |
|---------|------|
| `IIS 241` | Cycles |
| `IIS 242` | Pendulum |
| `IIS 243` | Gravity |
| `IIS 244` | Spring |
| `IIS 245` | Orbit |
| `IIS 246` | Swing |
| `IIS 247` | Euclidean |
| `IIS 248` | Bounce |
| `IIS 249` | Drunk |
| `IIS 250` | Chaos |
| `IIS 251` | Probability |

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

### State 1 (Velocity / Trigger) per Mode

For rhythm modes, State 1 doubles as a trigger-fired flag:

| Mode | State 1 Meaning | Range |
|------|-----------------|-------|
| Cycles | Speed × 2500 | ±5000 |
| Pendulum | Particle velocity | ±5000 |
| Gravity | Particle velocity | ±5000 |
| Spring | Particle velocity | ±5000 |
| Orbit | Angular velocity | ±5000 |
| Swing | Angular velocity ω | ±5000 |
| Euclidean | Trigger fired this frame | 5000 = yes, 0 = no |
| Bounce | Ball velocity × 100 | ±5000 |
| Drunk | Last step direction × step_size × 100 | ±5000 |
| Chaos | Lorenz Y value × 100 | ±5000 |
| Probability | Gate fired this frame | 5000 = yes, 0 = no |

### State 2 (Angle / Event Flag) per Mode

| Mode | State 2 Meaning | Range |
|------|-----------------|-------|
| Swing | Angle θ (±π/2 → ±5000) | ±5000 |
| Pendulum | Angle (asin of displacement) | ±5000 |
| Bounce | Floor-hit flag this frame | 5000 = yes, 0 = no |
| Chaos | Lorenz Z value × 100 | ±5000 |
| others | — (always 0) | 0 |

### Param1 (State 3) per Mode

| Mode | Param1 Content | Range |
|------|----------------|-------|
| Cycles | — (always 0) | 0 |
| Pendulum | Oscillation period | ms (1000–2500) |
| Gravity | Gravity strength × 500 | 0–5000 |
| Spring | Spring constant k × 1000 | 100–5000 |
| Orbit | Orbital period | ms (1000–2500) |
| Swing | Damping coefficient × 2500 | 0–5000 |
| Euclidean | Active beats k / n × 5000 | 0–5000 |
| Bounce | Ball position (0–5000) | 0–5000 |
| Drunk | Step size × 312 (0–16 → 0–5000) | 0–5000 |
| Chaos | ρ (rho) / 60 × 5000 | 0–5000 |
| Probability | Probability × 5000 | 0–5000 |

---

## Examples

```
; Set address once
IIA 49

; All rings → Swing mode
IIS 6

; All rings → Euclidean mode
IIS 7

; All rings → Chaos (IIS 50 because IIS 10 clashes with IIQ register)
IIS 50

; Ring 1 → Euclidean, Ring 2 → Bounce, Ring 3 → Chaos, Ring 4 → Probability
IIS 107
IIS 208
IIS 230
IIS 251

; Read position of Ring 1 (state 0)
IIQ 10   ; returns 0–5000

; Read angular velocity of Ring 3 (state 1)
IIQ 31   ; returns −5000…+5000

; Read Euclidean trigger fired on Ring 1 (state 1)
IIQ 11   ; returns 5000 if trigger fired this frame, else 0

; Read probability gate fired on Ring 4 (state 1)
IIQ 41   ; returns 5000 = fired, 0 = not

; Read ball floor-hit on Ring 2 (state 2, Bounce mode)
IIQ 22   ; returns 5000 = bounced this frame

; Read current probability of Ring 4 (state 3)
IIQ 43   ; 0–5000 = 0–100%

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
; Ring 1 Euclidean, Ring 2 Bounce, Ring 3 Drunk, Ring 4 Probability
IIS 107
IIS 208
IIS 229
IIS 251

; METRO (every ~16 ms via EVERY 1)
; Fire TR 1 on Euclidean beat
X IIQ 11
IF GT X 0: TR.PULSE 1

; Fire TR 2 on ball bounce
Y IIQ 22
IF GT Y 0: TR.PULSE 2

; Fire TR 3 on probability gate
Z IIQ 41
IF GT Z 0: TR.PULSE 3

; Use Drunk walk position as CV
CV 1 DIV MUL (IIQ 30) V 10 5000
```

---

## Notes

- The Arduino resets when the serial connection is opened (~2 s boot time). Queries during the first seconds after Pi startup may return 0.
- All values scale to **0–5000** (unsigned) or **±5000** (signed) for direct use as Teletype variables.
- IIQ always returns the state of whatever mode is active on that ring, even if rings are in different modes.
- Holding Encoder 0 (Ring 1 encoder) for more than 2 seconds shuts down the Pi — without Teletype.
- Per-ring mode can also be set in `config.yaml` under `ring_modes` for persistent startup configuration.
