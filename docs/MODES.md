
# Mode Concepts — Arc Cycles

Collected ideas for the system: Raspberry Pi A+ (physics/logic), Arduino Nano (I2C bridge), monome Teletype (CV/Gate).

---

## PART A — Single-Ring Modes (implementable)

Each of these works as an independent per-ring instance. Can be assigned individually with `IIS 1xx / 2xx / 3xx / 4xx`.

---

### Mode 7 — Euclidean Rhythm

The Euclidean algorithm distributes `k` active beats as evenly as possible over `n` steps.

- **Arc interface:** Encoder turn changes the number of active beats `k`. Loop length `n` is fixed per ring (e.g. 16 / 12 / 8 / 5) or adjustable via IIS. A playhead dot runs around the ring.
- **LED feedback:** Running playhead (bright). Active trigger positions glow dim. When the playhead hits a trigger, the LED flashes to maximum.
- **IIQ state:** State 0 = current playhead position. State 1 = whether a trigger fired this frame (5000 = yes, 0 = no). State 3 = active beats k (0–5000 scaled).
- **Teletype use:** `IF GT (IIQ 49 11) 0: TR.PULSE 1` — fires gate when ring 1 triggers.
- **Clock:** Internal clock running at configurable tempo (BPM via IIS command). No external clock input required.

---

### Mode 8 — Bouncing Ball Rhythm

A simulated ball thrown upward falls under gravity and bounces off the floor with energy loss. As the ball decelerates, the intervals between bounces get shorter — producing the classic organic "dribble" rhythm.

- **Arc interface:** Encoder turn = throw velocity (clockwise = stronger throw). Encoder press = reset.
- **LED feedback:** Ball height is shown as LED position on the ring.
- **IIQ state:** State 0 = ball position. State 1 = velocity. State 3 = floor-hit flag (5000 = hit this frame).
- **Teletype use:** Poll floor-hit flag, fire gate on bounce.
- **Note:** Gravity and elasticity (bounce damping) are fixed constants. In the original concept these were encoder-controlled, but that requires 3 rings → simplified here to single-ring.

---

### Mode 9 — Drunk Walk (Brownian Motion)

A value wanders randomly from step to step, constrained within boundaries. Produces slow, organic random motion — ideal for filter sweeps, micro-tonal variation, slow modulation sources.

- **Arc interface:** Encoder turn changes step size (how far the value wanders per frame). Wide turns = large jumps. Slow turns = small creep.
- **LED feedback:** Bright dot at current position, faint trail.
- **IIQ state:** State 0 = current position (0–5000). State 1 = current step direction/velocity.
- **Boundaries:** Soft walls — value reflects when it hits position 0 or 63.

---

### Mode 10 — Chaos Attractor (Lorenz)

A Lorenz strange attractor is computed in 3D. The X-coordinate is projected onto the ring. The path never repeats exactly — unlike a standard LFO, it is neither rigid nor pure noise. Produces slow, organic modulation arcs.

- **Arc interface:** Encoder turn changes the `ρ` (rho) parameter of the Lorenz system — effectively the "strength" of the chaotic attractor. Different values produce radically different orbits.
- **LED feedback:** Bright dot at projected position + short trail.
- **IIQ state:** State 0 = X position (0–5000). State 1 = Y value (±5000). State 2 = Z value (±5000).

---

### Mode 11 — Probability Gate (Bernoulli)

The ring displays a probability percentage as a filled arc. A trigger is "virtually" present on each internal clock tick; the probability value determines whether it passes through. Readable as a state value via IIQ.

- **Arc interface:** Encoder turn sets probability: 0% (fully left) to 100% (fully right).
- **LED feedback:** Filled arc from position 0 to current probability. When a trigger fires, the entire ring flashes briefly.
- **IIQ state:** State 0 = current probability (0–5000). State 1 = trigger fired this frame (5000 = yes). 
- **Teletype use:** `IF GT (IIQ 49 11) 0: TR.PULSE 1`

---

## PART B — Multi-Ring Modes (implementiert)

Diese Modi übernehmen alle 4 Ringe gleichzeitig. Aktivierung via `IIS 12–14`.  
Zurück zu Single-Ring: `IIS 1–11`.

---

### IIS 12 — Phase Shift (Steve Reich)

Zwei Paare [Ringe 0+1] und [Ringe 2+3] drehen sich mit leicht unterschiedlichen Geschwindigkeiten. Die Phasendifferenz driftet langsam — von unisono bis maximaler Versatz und zurück.

- **Encoder Ring 0:** Basisgeschwindigkeit (0–30 LED/s, Default 10)
- **Encoder Ring 1:** Drift-Rate — wie schnell die Phase wandert (0–10 LED/s, Default 1.5)
- **Press:** Ringe neu ausrichten (Phase auf 0, Defaults zurücksetzen)
- **Display:** Heller Punkt mit Trail. Bei Phasenübereinstimmung (< 1.5 LED Differenz): Helligkeitsboost
- **IIQ x0:** Rotationsposition des jeweiligen Rings (0–5000)
- **IIQ x1:** Phasendifferenz innerhalb des Paares (0 = in Phase, 5000 = max. Versatz)

---

### IIS 13 — Turing Machine 2×2

Zwei unabhängige Shift-Register (A auf Ringen 0+1, B auf Ringen 2+3). Unterschiedliche Loop-Längen erzeugen einen sich langsam verschiebenden Interferenz-Rhythmus.

- **Encoder Inhalt-Ring (0 / 2):** Mutations-Rate 0–100% (wie oft das letzte Bit neu gewürfelt wird)
- **Encoder Status-Ring (1 / 3):** Loop-Länge [7, 8, 9, 10, 11, 12, 16, 24, 32] (Default A=16, B=12 → LCM=48)
- **Press:** Register neu randomisieren + Playhead Reset
- **Display:** Ring 0/2 = Bitinhalt als Segmente + Playhead. Ring 1/3 = Mutations-Rate als Füllbogen + Playhead-Echo
- **IIQ x0:** Output-Bit des Registers (0 / 5000)
- **IIQ x1:** Mutations-Rate (0–5000)

---

### IIS 14 — Meadowphysics (Rhizomatisches Kaskaden-Netzwerk)

Vier unabhängige Countdown-Zähler, je einer pro Ring. Wenn ein Ring feuert, wird zusätzlich der nächste Ring zurückgesetzt (Kaskade: 0→1→2→3). Aus unterschiedlichen Perioden entstehen komplexe Überlagerungs-Rhythmen.

- **Encoder Turn:** Periode dieses Rings ändern (2–32 Schritte, bei 4 Hz = 0.5–8 s)
- **Press:** Diesen Zähler manuell zurücksetzen
- **Display:** Füllender Bogen (leer = gerade gestartet, voll = kurz vor dem Feuern). Kurzer Flash beim Feuern. Kleiner Pip bei Position 0 als Referenz.
- **Kaskade (fest):** Ring 0 feuert → Reset Ring 1 · Ring 1 feuert → Reset Ring 2 · Ring 2 feuert → Reset Ring 3
- **Default-Perioden:** Ring 0=4, Ring 1=6, Ring 2=8, Ring 3=12 Schritte
- **IIQ x0:** Trigger — 5000 wenn dieser Ring gerade gefeuert hat, sonst 0
- **IIQ x1:** Füllstand 0–5000 (kontinuierlich)

---

## PART C — Multi-Ring Modes (geplant / nicht implementiert)

---

### Step Sequencer (16/32-Step, CV-coupled)

A circular step sequencer. Encoder turn moves a cursor. Encoder press sets/clears a step. Two-layer mode: layer 1 = on/off, layer 2 = LED brightness = CV value.

- **Why postponed:** Complex UX (cursor + edit mode + playback simultaneously on one ring). Needs careful press/hold/turn interaction design.

---

### Bouncing Ball — Multi-Parameter Version

The original concept uses 3 encoders explicitly: Ring 1 = throw strength, Ring 2 = gravity, Ring 3 = elasticity (bounce damping). The rhythm emerges from the interplay.

- **Why multi-ring:** The 3-encoder parameter structure is the concept's defining feature.
- **Note:** A simplified single-ring version is implemented as Mode 8 above.

---

### Clock Multiplier / Divider & Ratcheting

Teletype provides a master clock. The Pi calculates exact multiplied/divided clock outputs. Encoder left = divide (/2, /3, /4, /8), center = 1:1, right = multiply (×2, ×3, ×4, ×8).

- **Why postponed:** Requires external clock input from Teletype → Arduino → Pi (reverse data flow, currently unimplemented). Also: each ring as an independent clock divider is possible, but the "center = 1:1" visual and tight timing requirements need more design.

---

### Topographic Voltage Fields (Map Sequencer)

A 2D landscape is generated. A virtual walker's X/Y coordinates produce two independent CV values (pitch + filter). Ring 1+2 = X and Y axis.

- **Why multi-ring:** Fundamentally a 2-coordinate system across 2+ rings.

---

### Neural Network (Trigger Cascade)

A single trigger cascades through a network of simulated neurons across rings, each firing with a delay and losing energy until silence returns. Creates stochastic cloud-like trigger patterns.

- **Why multi-ring:** The cascade propagates from ring to ring. A single ring would just be a decaying one-shot.

---

### Vector Rhythm (Quad XY Trigger)

Encoders 1+2 = X/Y position of a virtual gravity center. Encoders 3+4 = repulsion from walls. When the simulated point crosses one of four axes, the corresponding `TR` output fires.

- **Why multi-ring:** All 4 encoders form one shared 2D coordinate system. Individual ring assignment makes no sense.

---

### Viscosity (Coupled Inertia)

Not a standalone mode — an input processing concept. Encoder turns don't change values directly but change the density of a virtual fluid the control signal moves through. Fast turns build pressure; the value follows slowly.

- **Why postponed:** This is a meta-feature (encoder input smoothing) that could be applied to any mode. Better implemented as a global option than a mode.

---

## IIS Command Scheme — 3-Digit Extension

To support all 12 modes with per-ring assignment, the existing 2-digit IIS scheme (IIS 11–46) is extended to a 3-digit range.

### All-Ring Mode Switch (unchanged)

| IIS | Mode |
|-----|------|
| `IIS 1–6` | Modes 1–6 (Cycles through Swing) — all rings |
| `IIS 7` | Euclidean — all rings |
| `IIS 8` | Bouncing Ball — all rings |
| `IIS 9` | Drunk Walk — all rings |
| `IIS 10` | Chaos Attractor — all rings |
| `IIS 11` | Probability Gate — all rings |

*Note: IIS 10 and 11 conflict with the old per-ring scheme (IIS 11 was Ring 1 → Cycles). The new 3-digit per-ring scheme below replaces IIS 11–46.*

### Per-Ring Mode Switch — 3-Digit Scheme

Byte range 100–172. Each ring gets a block of 20 slots (supports up to 20 modes per ring).

```
Ring 1: IIS 101–112   (101 + mode - 1)
Ring 2: IIS 121–132   (121 + mode - 1)
Ring 3: IIS 141–152   (141 + mode - 1)
Ring 4: IIS 161–172   (161 + mode - 1)
```

| IIS | Ring | Mode |
|-----|------|------|
| 101 | 1 | Cycles |
| 102 | 1 | Pendulum |
| 103 | 1 | Gravity |
| 104 | 1 | Spring |
| 105 | 1 | Orbit |
| 106 | 1 | Swing |
| 107 | 1 | Euclidean |
| 108 | 1 | Bouncing Ball |
| 109 | 1 | Drunk Walk |
| 110 | 1 | Chaos Attractor |
| 111 | 1 | Probability Gate |
| 121 | 2 | Cycles |
| … | … | … |
| 131 | 2 | Probability Gate |
| 141 | 3 | Cycles |
| … | … | … |
| 151 | 3 | Probability Gate |
| 161 | 4 | Cycles |
| … | … | … |
| 171 | 4 | Probability Gate |

Decode formula: `ring = (cmd - 101) // 20`, `mode = (cmd - 101) % 20 + 1`
