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

Teletype writes **1 byte** to the Arduino. The command code itself is the value.

### Switch Mode — All Rings (Single-Ring Modi)

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
| `IIS 10` | Chaos — Lorenz attractor |
| `IIS 11` | Probability — Bernoulli gate |

### Switch Mode — Multi-Ring Modi

Aktivieren eines Multi-Ring-Modus übernimmt alle 4 Ringe. Einzel-Ring-Modi werden pausiert bis der Multi-Modus per `IIS 1–11` beendet wird.

| Command | Modus |
|---------|-------|
| `IIS 12` | Phase Shift — Steve Reich, 2 Paare [0,1] + [2,3] |
| `IIS 13` | Turing Machine 2×2 — zwei Shift-Register auf je 2 Ringen |
| `IIS 14` | Meadowphysics — rhizomatisches Kaskaden-Zähler-Netzwerk (4 Ringe) |
| `IIS 15` | reserviert |

### Clock Tick (für Clock Div/Mul)

| Command | Effect |
|---------|--------|
| `IIS 88` | Externer Clock-Tick — Teletype takt an Pi melden |

### Switch Mode — Single Ring

Teletype IIS überträgt ein einzelnes Byte (max 255).  
Rings 1 und 2 nutzen `1xx` / `2xx` Präfixe. Ringe 3 und 4 können nicht `3xx` / `4xx` verwenden (> 255) und liegen daher im oberen 200er-Bereich.

**Ring 1 — IIS 101–111**

| IIS | Mode |
|-----|------|
| 101 | Cycles |
| 102 | Pendulum |
| 103 | Gravity |
| 104 | Spring |
| 105 | Orbit |
| 106 | Swing |
| 107 | Euclidean |
| 108 | Bounce |
| 109 | Drunk |
| 110 | Chaos |
| 111 | Probability |

**Ring 2 — IIS 201–211**

| IIS | Mode |
|-----|------|
| 201 | Cycles |
| 202 | Pendulum |
| 203 | Gravity |
| 204 | Spring |
| 205 | Orbit |
| 206 | Swing |
| 207 | Euclidean |
| 208 | Bounce |
| 209 | Drunk |
| 210 | Chaos |
| 211 | Probability |

**Ring 3 — IIS 221–231**

| IIS | Mode |
|-----|------|
| 221 | Cycles |
| 222 | Pendulum |
| 223 | Gravity |
| 224 | Spring |
| 225 | Orbit |
| 226 | Swing |
| 227 | Euclidean |
| 228 | Bounce |
| 229 | Drunk |
| 230 | Chaos |
| 231 | Probability |

**Ring 4 — IIS 241–251**

| IIS | Mode |
|-----|------|
| 241 | Cycles |
| 242 | Pendulum |
| 243 | Gravity |
| 244 | Spring |
| 245 | Orbit |
| 246 | Swing |
| 247 | Euclidean |
| 248 | Bounce |
| 249 | Drunk |
| 250 | Chaos |
| 251 | Probability |

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

Teletype writes a register code and reads back 2 bytes (int16, big-endian).  
Return range: **0–5000** (unsigned) or **−5000–+5000** (signed).

Each ring reports the state of whatever mode is currently running on it.

### Register Scheme

```
Register = (Ring + 2) × 10 + State
```

| Register | Ring | State |
|----------|------|-------|
| 20–23 | 0 (Ring 1) | 0–3 |
| 30–33 | 1 (Ring 2) | 0–3 |
| 40–43 | 2 (Ring 3) | 0–3 |
| 50–53 | 3 (Ring 4) | 0–3 |

> **Hinweis:** IIQ startet bei 20 (nicht 10), da IIS 10–15 für Modi-Befehle reserviert sind. Beide Systeme nutzen denselben Byte-Kanal vom Arduino.

### State Definitions

| State | Name | Description | Range |
|-------|------|-------------|-------|
| 0 | Position | Current LED position (0–63 → 0–5000) | 0 … 5000 |
| 1 | Velocity / Trigger | Speed, angular velocity, or trigger flag | −5000 … +5000 |
| 2 | Angle / Event | Angle or event flag (mode-dependent) | −5000 … +5000 |
| 3 | Param1 | Mode-specific parameter | 0 … 5000 |

### State 1 (Velocity / Trigger) per Mode

| Mode | State 1 | Range |
|------|---------|-------|
| Cycles | Speed × 2500 | ±5000 |
| Pendulum | Particle velocity | ±5000 |
| Gravity | Particle velocity | ±5000 |
| Spring | Particle velocity | ±5000 |
| Orbit | Angular velocity | ±5000 |
| Swing | Angular velocity ω | ±5000 |
| Euclidean | Trigger fired this frame | 5000 / 0 |
| Bounce | Ball velocity × 100 | ±5000 |
| Drunk | Last step × step_size × 100 | ±5000 |
| Chaos | Lorenz Y × 100 | ±5000 |
| Probability | Gate fired this frame | 5000 / 0 |

### State 2 (Angle / Event Flag) per Mode

| Mode | State 2 | Range |
|------|---------|-------|
| Swing | Angle θ (±π/2 → ±5000) | ±5000 |
| Pendulum | Angle (asin of displacement) | ±5000 |
| Bounce | Floor-hit flag this frame | 5000 / 0 |
| Chaos | Lorenz Z × 100 | ±5000 |
| others | — (always 0) | 0 |

### Param1 (State 3) per Mode

| Mode | Param1 | Range |
|------|--------|-------|
| Cycles | — | 0 |
| Pendulum | Period in ms | 1000–2500 |
| Gravity | Gravity × 500 | 0–5000 |
| Spring | Spring constant k × 1000 | 100–5000 |
| Orbit | Period in ms | 1000–2500 |
| Swing | Damping × 2500 | 0–5000 |
| Euclidean | Active beats k/n × 5000 | 0–5000 |
| Bounce | Ball position | 0–5000 |
| Drunk | Step size × 312 | 0–5000 |
| Chaos | ρ / 60 × 5000 | 0–5000 |
| Probability | Probability × 5000 | 0–5000 |

---

## IIQ — Multi-Ring Modi

Wenn ein Multi-Ring-Modus aktiv ist, liefern die IIQ-Register modusspezifische Werte statt der Single-Ring-Physik.

### Phase Shift (IIS 12)

Ringe 0+1 = Paar A, Ringe 2+3 = Paar B. Jedes Paar ist unabhängig.

| Register | Ring | State 0 (pos) | State 1 (vel) |
|----------|------|---------------|---------------|
| `IIQ 49 20` | Ring 0 | Rotationsposition A (0–5000) | Phasendifferenz A↔B (0–5000) |
| `IIQ 49 30` | Ring 1 | Rotationsposition A (0–5000) | Phasendifferenz A↔B (0–5000) |
| `IIQ 49 40` | Ring 2 | Rotationsposition B (0–5000) | Phasendifferenz C↔D (0–5000) |
| `IIQ 49 50` | Ring 3 | Rotationsposition B (0–5000) | Phasendifferenz C↔D (0–5000) |

Encoder Ring 0: Basisgeschwindigkeit · Encoder Ring 1: Drift-Rate · Press: Ringe ausrichten

### Turing Machine 2×2 (IIS 13)

Register A auf Ringen 0+1, Register B auf Ringen 2+3.

| Register | Ring | State 0 (pos) | State 1 (vel) |
|----------|------|---------------|---------------|
| `IIQ 49 20` | Ring 0 | Output-Bit A (0 / 5000) | Mutations-Rate A (0–5000) |
| `IIQ 49 30` | Ring 1 | Output-Bit A (0 / 5000) | Mutations-Rate A (0–5000) |
| `IIQ 49 40` | Ring 2 | Output-Bit B (0 / 5000) | Mutations-Rate B (0–5000) |
| `IIQ 49 50` | Ring 3 | Output-Bit B (0 / 5000) | Mutations-Rate B (0–5000) |

Encoder Inhalts-Ring (0/2): Mutations-Rate · Encoder Status-Ring (1/3): Loop-Länge · Press: Register neu randomisieren

### Meadowphysics (IIS 14)

4 unabhängige Countdown-Zähler. Ring N feuert → Reset Ring N+1 (Kaskade).

| Register | Ring | State 0 (pos) | State 1 (vel) |
|----------|------|---------------|---------------|
| `IIQ 49 20` | Ring 0 | Trigger (5000 = gefeuert) | **Füllstand (0–5000)** |
| `IIQ 49 30` | Ring 1 | Trigger (5000 = gefeuert) | **Füllstand (0–5000)** |
| `IIQ 49 40` | Ring 2 | Trigger (5000 = gefeuert) | **Füllstand (0–5000)** |
| `IIQ 49 50` | Ring 3 | Trigger (5000 = gefeuert) | **Füllstand (0–5000)** |

Encoder Turn: Periode ändern (2–32 Schritte, ~0.5–8 s bei 4 Hz) · Press: Zähler zurücksetzen

---

## Examples

```
; Set address once
IIA 49

; All rings → Swing mode
IIS 6

; All rings → Euclidean
IIS 7

; All rings → Chaos
IIS 10

; All rings → Probability
IIS 11

; Ring 1 → Euclidean, Ring 2 → Bounce, Ring 3 → Chaos, Ring 4 → Probability
IIS 107
IIS 208
IIS 230
IIS 251

; Read position of Ring 1 (state 0)
IIQ 20   ; returns 0–5000

; Read velocity of Ring 1 (state 1)
IIQ 21   ; returns ±5000

; Read Euclidean trigger fired on Ring 1
IIQ 21   ; 5000 = fired this frame

; Read probability gate fired on Ring 4
IIQ 51   ; 5000 = fired, 0 = not

; Read ball floor-hit on Ring 2 (state 2, Bounce mode)
IIQ 32   ; 5000 = bounced this frame

; Read current probability of Ring 4 (state 3)
IIQ 53   ; 0–5000 = 0–100%

; Meadowphysics aktivieren
IIS 14

; Trigger von Ring 0 lesen (State 0)
IIQ 20   ; 5000 = gerade gefeuert

; Füllstand Ring 2 lesen (State 1)
IIQ 41   ; 0–5000

; Phase Shift aktivieren
IIS 12

; Phasendifferenz lesen (State 1, Ring 0)
IIQ 21   ; 0 = in Phase, 5000 = maximaler Versatz

; Zurück zu Single-Ring
IIS 1

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

; METRO — fire TR outputs from ring states
; TR 1 on Euclidean beat (Ring 1 state 1)
X IIQ 21
IF GT X 0: TR.PULSE 1

; TR 2 on ball bounce (Ring 2 state 2)
Y IIQ 32
IF GT Y 0: TR.PULSE 2

; TR 3 on probability gate (Ring 4 state 1)
Z IIQ 51
IF GT Z 0: TR.PULSE 3

; CV 1 from Drunk walk position (Ring 3 state 0)
CV 1 DIV MUL (IIQ 40) V 10 5000
```

---

## Notes

- The Arduino resets when the serial connection is opened (~2 s boot time). Queries during the first seconds after Pi startup may return 0.
- All values scale to **0–5000** (unsigned) or **±5000** (signed) for direct use as Teletype variables.
- IIQ always returns the state of whatever mode is active on that ring, even if rings are in different modes.
- Holding Encoder 0 (Ring 1 encoder) for more than 2 seconds shuts down the Pi — without Teletype.
- Per-ring mode can also be set in `config.yaml` under `ring_modes` for persistent startup configuration.

- **IIS 12–14** (multi-ring modes) sind aktiv. IIS 15 ist reserviert.
- Bei aktiven Multi-Ring-Modi liefern IIQ-Register modusspezifische Werte (siehe Abschnitt oben). Einzelring-Physikwerte sind während dieser Zeit nicht verfügbar.
