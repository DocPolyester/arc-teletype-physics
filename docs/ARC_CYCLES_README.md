# Arc Cycles - Physik-basierte Multi-Mode Arc App

Eine **physics-basierte Arc-Anwendung** mit mehreren Interaktionsmodi:

## Modi

### 1. **Cycles Mode** (Default)
Klassisch wie Monome Cycles - vier unabhängige rotierende Positionen mit Momentum.
- Drehbewegung erzeugt Schwung
- Langsames Ausbremsen (Reibung)
- Press zum Zurücksetzen
- Trail-Effekt für visuelle Kontinuität

**Teletype Befehle:**
```
CYCLES.RESET              # Alle rings zurücksetzen
CYCLES.SPEED 0 10         # Ring 0, Speed 10
CYCLES.POS 0 32           # Ring 0, Position 32
```

### 2. **Pendulum Mode** 🎛️
Vier unabhängige Pendel mit unterschiedlichen Schwingungsperioden. Schwerkraft + Oszillation.
- Ring 0: 1.0s Periode (schnell)
- Ring 1: 1.5s
- Ring 2: 2.0s
- Ring 3: 2.5s (langsam)

Drehbewegung gibt dem Pendel Energie (Impuls).

**Teletype Befehle:**
```
PEND.PERIOD 0 500         # Ring 0, 500ms Periode
PEND.AMP 0 20             # Amplitude 20 (0-32)
PEND.RESET                # Alle zurücksetzen
```

### 3. **Gravity Mode** 🪨
Mehrere Partikel "fallen" unter Schwerkraft zum unteren Rand (Position 32).
- 4 Partikel pro Ring mit unterschiedlichen Massen
- Pralleffekt bei Rändern
- Drehbewegung gibt Aufwärtsimpuls
- Glow-Effekt um Partikel

**Teletype Befehle:**
```
GRAV.STRENGTH 5           # Schwerkraft-Intensität (0-10)
GRAV.RESET                # Alle Partikel oben zurücksetzen
```

### 4. **Spring Mode** 🔄
Partikel werden zum Zentrum (Position 32) "gezogen" wie Federn.
- Resonanz-Effekt: Drehen erzeugt Schwingungen
- Mehrere Partikel pro Ring
- Resonanzenergie klingt langsam ab
- Heller beim Schwingen

**Teletype Befehle:**
```
SPRING.K 0 2.5            # Federsteifigkeit (0.1-5.0)
SPRING.CENTER 0 32        # Mittenpunkt
SPRING.RESET              # Alle zentrieren
```

### 5. **Orbit Mode** 🌍
Partikel umkreisen einen zentralen Punkt wie Planeten.
- Unterschiedliche Orbitalperioden pro Ring
- Drehbewegung ändert Orbitalgeschwindigkeit
- 3D-Effekt durch variable Helligkeit
- Zentrum dunkel gekennzeichnet

**Teletype Befehle:**
```
ORBIT.PERIOD 0 1000       # Ring 0, 1000ms Orbitalperiode
ORBIT.RADIUS 0 16         # Orbitradius
ORBIT.PARTICLES 0 3       # 3 umkreisende Körper
```

## Mode-Auswahl

### Via Fader (Fader 0)
Fader 0 steuert den Mode:
- Fader oben: **Cycles**
- Fader oben-Mitte: **Pendulum**
- Fader Mitte: **Gravity**
- Fader Unten-Mitte: **Spring**
- Fader unten: **Orbit**

### Via Teletype
```
MODE.CYCLES               # Zu Cycles wechseln
MODE.PENDULUM             # Zu Pendulum wechseln
MODE.GRAVITY
MODE.SPRING
MODE.ORBIT
```

## Encoder Interaktion

Alle Encoder sind pro Mode unterschiedlich:

| Ring | Action | Cycles | Pendulum | Gravity | Spring | Orbit |
|------|--------|--------|----------|---------|--------|-------|
| **Drehen** | Rotation | Position ändern + Momentum | Pendel anstoßen | Partikel hochwerfen | Resonanz excite | Orbitalgeschwindigkeit |
| **Press** | Reset | Position 0 | Center | Top reset | Center | Orbit reset |

## Teletype Integration

Jeder Mode kann von Teletype aus gesteuert werden:

```teletype
# Beispiele:
CYCLES.POS 0 16           # Ring 0 zu Position 16
PEND.PERIOD 1 1500        # Pendulum Ring 1: 1500ms
GRAV.STRENGTH 7
MODE.SPRING               # Zu Spring Mode wechseln
```

## Konfiguration

Bearbeite `config.yaml` um Adressen anzupassen:

```yaml
devices:
  tio:
    enabled: true
  faders:
    enabled: true
  teletype:
    enabled: true
```

## Verbindung mit TIO

Die Apps können auch Ausgaben auf die TIO senden (optional):

```python
tio = middleware.get_tio()

# CV Output basierend auf Arc Position
position = app.current_mode.positions[0]  # 0-63
cv_value = int((position / 64) * 4095)    # 0-4095 (12-bit)
tio.set_cv(0, cv_value)
```

## Starten

```bash
# Auf dem Pi:
python3 src/arc_cycles_app.py

# Oder über Systemd:
sudo systemctl start arc-middleware  # wenn konfiguriert
```

## Debugging

```bash
# Live logs
tail -f logs/arc_cycles.log

# Via SSH + Logs Task
# Cmd+Shift+P → "View Logs"
```

## Auswirkungen auf Ideen

### Weitere mögliche Modi

1. **Wave Mode** - Wellenausbreitung vom Zentrum
2. **Chaos Mode** - Strange attractor, Lorenz equations
3. **N-Body Mode** - Mehrkörper-Gravitation
4. **Magnetic Mode** - Magnetische Anziehung/Abstoßung
5. **Flocking Mode** - Schwarmverhalten

Jeder neue Mode kann in `src/apps/arc_cycles/modes/` als neue Klasse hinzugefügt werden.

## Code-Struktur

```
src/
├── apps/
│   └── arc_cycles/
│       ├── physics.py              # Physics Engine
│       ├── mode_base.py            # Base class
│       ├── main.py                 # App coordinator
│       └── modes/
│           ├── cycles_mode.py
│           ├── pendulum_mode.py
│           ├── gravity_mode.py
│           ├── spring_mode.py
│           └── orbit_mode.py
├── arc_cycles_app.py               # Entry point
└── middleware.py                   # Hardware integration
```

---

**Viel Spaß mit den physikalischen Effekten! 🎛️**

Experimentiere mit den Perioden, Stärken und Massen-Verhältnissen für neue Patterns.
