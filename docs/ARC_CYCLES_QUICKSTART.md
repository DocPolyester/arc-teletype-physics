# Quick Start: Arc Cycles Physics App

Eine **vollständige, einsatzbereite Physics-Simulation für deinen Arc Clone**!

## Was ist neu?

✨ **5 Physics Modi** basierend auf echten Simulationen:
- **Cycles**: Klassisch wie Original
- **Pendulum**: Schwerkraft + Oszillation
- **Gravity**: Fallende Partikel
- **Spring**: Federmechanik/Resonanz
- **Orbit**: Orbitalphysik

## Installation (3 Schritte)

### 1. SSH Extension installieren

In VS Code:
```vscode-extensions
ms-vscode-remote.remote-ssh,ms-vscode.remote-explorer
```

Dann: **Cmd+Shift+P** → "Remote-SSH: Connect to Host" → `pi@monome-arc.local`

### 2. Arc Cycles deployen

```bash
# Im Projekt:
Ctrl+Shift+B  # Deploy all files
```

### 3. Auf dem Pi starten

```bash
# Option A: Direkter Start
ssh pi@monome-arc.local 'python3 /home/pi/arc-middleware/src/arc_cycles_app.py'

# Option B: Teletype Script nutzen (siehe unten)
```

## Bedienung

### Encoder (Arc)

Jeder Ring kann gedreht und gedrückt werden:

```
DREHEN   → Abhängig vom Mode (siehe Tabelle)
DRÜCKEN  → Reset/Zentrieren
```

### Fader 0: Mode-Auswahl

Position des Faders bestimmt den Mode:

```
█ oben     → CYCLES
  █        → PENDULUM
    █      → GRAVITY
      █    → SPRING
       █   → ORBIT unten
```

### Teletype: Direktes Control

```teletype
MODE.CYCLES               # Zu Cycles wechseln
PEND.PERIOD 0 1000       # Pendulum: Ring 0, 1s Periode
GRAV.STRENGTH 6          # Gravity: Stärke 6
SPRING.K 0 2.5           # Spring: Federsteifigkeit
ORBIT.PARTICLES 2 4      # Orbit: Ring 2, 4 Partikel
```

## Teletype Script Beispiele

Sieh [teletype_examples.tt](teletype_examples.tt) für vollständige Patterns:

```teletype
# Auto-Mode Cycling (5s pro Mode)
METRO 5000 1
M (M + 1)
IF M > 4 : M 0
IF M 0 : MODE.CYCLES
IF M 1 : MODE.PEND
IF M 2 : MODE.GRAV
IF M 3 : MODE.SPRING
IF M 4 : MODE.ORBIT

# Gravity mit Fader 0 Control
METRO 50 1
GRAV.STRENGTH (N 0 / 6554)  # 0-10
```

## File Struktur

```
src/
├── arc_cycles_app.py                    ← Startpunkt
├── apps/
│   └── arc_cycles/
│       ├── physics.py                   ← Physics Engine
│       ├── mode_base.py                 ← Mode Base Class
│       ├── main.py                      ← ArcCyclesApp Manager
│       └── modes/
│           ├── cycles_mode.py           ← Klassisch
│           ├── pendulum_mode.py         ← Schwerkraft
│           ├── gravity_mode.py          ← Fallende Partikel
│           ├── spring_mode.py           ← Federmechanik
│           └── orbit_mode.py            ← Orbitalphysik

docs/
├── ARC_CYCLES_README.md                 ← Detaillierte Modi-Doku
├── TELETYPE_INTEGRATION.md              ← Alle Teletype Befehle
└── teletype_examples.tt                 ← Teletype Script Beispiele
```

## Modi Übersicht

### Cycles (Default)
Wie das Original - Position mit Momentum. Press zum Reset.

### Pendulum
Vier unabhängige Pendel mit Schwerkraft. Drehen = Impuls. Unterschiedliche Perioden pro Ring.

### Gravity
Partikel fallen unter Schwerkraft. Prallen ab. Drehen = hochwerfen.

### Spring
Federm echanik: Partikel werden zum Zentrum gezogen. Resonanz-Effekt.

### Orbit
Planeten umkreisen einen Punkt. Drehen ändert Orbitalgeschwindigkeit.

## Konfiguration

Bearbeite `config.yaml` um Geräte-Adressen anzupassen:

```yaml
arc_host: "127.0.0.1"
arc_port: 8000
i2c_bus: 1

devices:
  tio:
    enabled: true
    address: 0x70
  faders:
    enabled: true
    address: 0x34
  teletype:
    enabled: true
    address: 0x20
```

## Debugging

```bash
# Logs live anschauen
tail -f /home/pi/arc-middleware/logs/arc_cycles.log

# Oder via VS Code:
# Cmd+Shift+P → "View Logs"

# SSH Connection testen
# Cmd+Shift+P → "Test SSH Connection"
```

## Nächste Schritte

1. ✅ Deploy: `Ctrl+Shift+B`
2. ✅ Starten: `ssh pi@monome-arc.local 'python3 /home/pi/arc-middleware/src/arc_cycles_app.py'`
3. ✅ Spielen: Encoder drehen, Fader 0 für Mode-Wechsel
4. ✅ Teletype Scripts schreiben: Siehe [teletype_examples.tt](teletype_examples.tt)

## Weitere Ideen

Weitere Modi können einfach hinzugefügt werden:

- Wave Mode
- Chaos/Strange Attractor
- N-Body Gravitation
- Magnetic Force
- Flocking/Swarm

Jeder neue Mode: Neue Klasse in `src/apps/arc_cycles/modes/`

---

**Viel Spaß mit deiner Physics-Arc! 🎛️**

Fang mit den Standard-Modi an, dann schreib deine eigenen Effekte!
