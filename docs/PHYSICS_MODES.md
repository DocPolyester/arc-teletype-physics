# Arc Cycles — Physics Modes

Six independent physics simulations drive the four rings of a monome Arc. Each ring behaves independently. Encoders interact with the simulation in real time.

---

## Hardware Note

All physics parameters are tuned for the **DIY Arc by [theslowgrowth](https://github.com/theslowgrowth)**, which generates less encoder ticks per revolution than the original monome Arc. If you use an original Arc, interactions will feel less aggressive — change the sensitivity constants in the mode files accordingly:

| Mode | File | Constant(s) to reduce |
|------|------|-----------------------|
| Cycles | `cycles_mode.py` | `SENSITIVITY`, `MAX_SPEED` |
| Pendulum | `pendulum_mode.py` | `encoder_force` multiplier (`delta * 2`) |
| Gravity | `gravity_mode.py` | `encoder_impulse` multiplier (`delta * 3`) |
| Spring | `spring_mode.py` | resonance increment (`abs(delta) * 0.5`) |
| Orbit | `orbit_mode.py` | angular accel increment (`delta * 0.3`) |
| Swing | `swing_mode.py` | `IMPULSE` |

## General Behavior

- **ARC display**: 64 LEDs per ring (0 = left/horizontal, 32 = right, clockwise)
- **Orientation**: default horizontal; switchable to portrait (270°) with `IIS 91`
- **Update rate**: ~60 Hz physics loop
- **Encoder press** (single ring): resets that ring's state
- **Encoder 0 + 1 pressed** (within 2 s): shuts down the Raspberry Pi

---

## Mode 1 — Cycles

Classic rotating dot with inertia and friction — similar to the Ansible Cycles algorithm.

**Physics:**  
Each ring has a speed value. Each frame the speed is multiplied by friction factor 0.985, so the ring gradually decelerates. One encoder tick adds ±0.05 to the speed (capped at ±2.0). The bright dot advances by the current speed each frame.

**Display:**  
One bright head pixel (brightness 15) + one dim trailing pixel (brightness 3).

**Encoder interaction:**  
- Turn: increase speed / reverse direction  
- Press: stop ring immediately (speed = 0)

**Teletype IIQ states:**

| State | Meaning | Range |
|-------|---------|-------|
| 0 | Dot position (0–63 → 0–5000) | 0 … 5000 |
| 1 | Current speed (±2 pos/frame) | −5000 … +5000 |
| 2 | Angle (unused) | 0 |
| 3 | Param1 (unused) | 0 |

---

## Mode 2 — Pendulum

Four harmonic pendulums (linear approximation) with different periods and staggered phases.

**Physics:**  
Each ring oscillates sinusoidally around position 32 with a configured period (default: 1.0 / 1.5 / 2.0 / 2.5 s) and an amplitude of ±16 LED positions. Phases are offset by π/2 so the four rings swing asynchronously. One encoder tick adds a brief disturbance force (decays over 10 frames).

**Display:**  
Bright spot (brightness 14) + short trail (6 → 4 → 2).

**Encoder interaction:**  
- Turn: apply a momentary impulse (temporarily affects amplitude)  
- Press: reset ring to rest position (position 32)

**Teletype IIQ states:**

| State | Meaning | Range |
|-------|---------|-------|
| 0 | Position (0–63 → 0–5000) | 0 … 5000 |
| 1 | Particle velocity | −5000 … +5000 |
| 2 | Angle (asin of displacement / amplitude × 5000/(π/2)) | −5000 … +5000 |
| 3 | Oscillation period in ms (1000–2500) | 1000 … 2500 |

---

## Mode 3 — Gravity

Four particles per ring fall under simulated gravity toward the "floor" (ring position 32) and bounce off the edges.

**Physics:**  
Each ring has 4 particles with slightly different masses (1.0 to 1.6). Gravity pulls them proportionally to their distance from position 32. At the edges (position < 2 or > 62) velocity is inverted with a damping factor of 0.7 (inelastic bounce). Gravity strength is globally configurable (default: 5.0).

**Display:**  
Each particle appears as a main dot plus 2 symmetric glow pixels on each side.

**Encoder interaction:**  
- Turn: apply an upward impulse to all particles on the ring  
- Press: redistribute particles evenly, velocity = 0

**Teletype IIQ states:**

| State | Meaning | Range |
|-------|---------|-------|
| 0 | Position of first particle | 0 … 5000 |
| 1 | Velocity of first particle | −5000 … +5000 |
| 2 | Angle (unused) | 0 |
| 3 | Gravity strength (0–10 → 0–5000) | 0 … 5000 |

---

## Mode 4 — Spring

Spring mechanics with resonance effects. Four particles per ring are pulled toward the center (position 32) by a spring. Encoder turns excite the system into resonance.

**Physics:**  
Spring force = `k × (center − position)` along the shortest path on the ring (±32 LEDs). A resonance energy overlays a sinusoidal perturbation and decays at 0.95 per frame. Particle velocity is scaled by damping factor 0.92. Spring constant k differs per ring (default: 2.0 / 2.2 / 1.8 / 2.0).

**Display:**  
Dim center marker (brightness 3) + particles whose brightness increases with resonance energy.

**Encoder interaction:**  
- Turn: increase resonance energy (max 5.0); more turning → stronger oscillation  
- Press: all particles to center, resonance = 0

**Teletype IIQ states:**

| State | Meaning | Range |
|-------|---------|-------|
| 0 | Position of first particle | 0 … 5000 |
| 1 | Velocity of first particle | −5000 … +5000 |
| 2 | Angle (unused) | 0 |
| 3 | Spring constant k × 1000 (k ≈ 0.1–5.0) | 100 … 5000 |

---

## Mode 5 — Orbit

Orbital mechanics model: multiple bodies orbit a center point on the ring. Encoder turns accelerate the orbit (like a gravity-assist maneuver).

**Physics:**  
Each ring has 3 or 4 evenly spaced bodies (default: rings 0+1 = 3 particles, rings 2+3 = 4 particles). Angular position = `ω × t + phase_offset`. Encoder input adds angular acceleration (decays at 0.98 per frame). Brightness varies with `cos(angle)` to create a 3D impression.

**Display:**  
Dim center point (brightness 2) + orbiting bodies with varying brightness (1–15).

**Encoder interaction:**  
- Turn: increase / decrease orbital speed  
- Press: reset angular acceleration and velocity to 0

**Teletype IIQ states:**

| State | Meaning | Range |
|-------|---------|-------|
| 0 | Center position (always 32 → ~2540) | ~2540 |
| 1 | Additional angular velocity | −5000 … +5000 |
| 2 | Angle (unused) | 0 |
| 3 | Orbital period in ms (1000–2500) | 1000 … 2500 |

---

## Mode 6 — Swing

Nonlinear pendulum with Runge-Kutta 4 integration. The exact pendulum ODE (no small-angle approximation) is simulated — at large amplitudes the nonlinearity becomes audible as a subtle period stretching.

**Physics:**  
ODE: `θ'' = −(g/L)·sin(θ) − b·θ'`  
with g = 9.8 m/s² and adjustable damping b (default: 0.4).  
Pendulum lengths for the four rings: 0.25 m / 1.0 m / 2.25 m / 4.0 m.  
Natural periods: ~1 s / 2 s / 3 s / 4 s.  
Angle θ maps to LED position: π/2 → ±20 LEDs from equilibrium (position 32).

**Display:**  
Bright main dot (brightness 6–15, proportional to current speed — brightest at center when speed is maximal). Trail of 5 pixels in the direction of travel. Dim equilibrium marker (brightness 1).

**Encoder interaction:**  
- Turn: add ±0.8 rad/s angular impulse per tick  
- Press: set θ and ω to 0 (pendulum at rest)

**Teletype IIQ states:**

| State | Meaning | Range |
|-------|---------|-------|
| 0 | LED position of pendulum bob | 0 … 5000 |
| 1 | Angular velocity ω (±π rad/s ≈ ±5000) | −5000 … +5000 |
| 2 | Angle θ (±π/2 → ±5000) | −5000 … +5000 |
| 3 | Damping coefficient b × 2500 (b = 0–2.0) | 0 … 5000 |

---

## Mode Overview

| Nr | Teletype | Name | Description |
|----|----------|------|-------------|
| 1 | `IIS 1` | Cycles | Rotating dot with inertia and friction |
| 2 | `IIS 2` | Pendulum | Harmonic pendulum, 4 different periods |
| 3 | `IIS 3` | Gravity | Particles under gravity with bouncing |
| 4 | `IIS 4` | Spring | Spring mechanics with resonance |
| 5 | `IIS 5` | Orbit | Orbital model / planetary system |
| 6 | `IIS 6` | Swing | Nonlinear pendulum (RK4) |
