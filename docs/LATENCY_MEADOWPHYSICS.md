# Latenz-Analyse: Meadowphysics Multi-Ring (IIS 14)

Letzte Messung / Annahmen: 2026-06-20  
Hardware: Raspberry Pi A+ (700 MHz, 1 Core) · Arduino Nano V3.0 · Monome Arc 4 · Monome Teletype

---

## Signalkette: Teletype `IIS 88` → Arc-LED sichtbar

```
Teletype                Arduino              RPi A+                  serialoscd            Arc
   │                       │                    │                        │                  │
   │─── I2C write ────────▶│                    │                        │                  │
   │   (IIS 88 = 0x58)     │                    │                        │                  │
   │   ~0.3 ms             │                    │                        │                  │
   │                       │─── Serial TX ─────▶│                        │                  │
   │                       │  4 Bytes @ 115200   │                        │                  │
   │                       │   0.35 ms           │                        │                  │
   │                       │                     │ _rx_loop wacht         │                  │
   │                       │                     │ select() → <1 ms       │                  │
   │                       │                     │ _do_step() + Event     │                  │
   │                       │                     │ ~0.1 ms                │                  │
   │                       │                     │                        │                  │
   │                       │                     │ main thread wacht auf  │                  │
   │                       │                     │ _tick_event: ~1-4 ms   │                  │
   │                       │                     │ (OS Scheduler Jitter)  │                  │
   │                       │                     │                        │                  │
   │                       │                     │ update() + display()   │                  │
   │                       │                     │ ~0.5 ms                │                  │
   │                       │                     │                        │                  │
   │                       │                     │─── UDP (localhost) ───▶│                  │
   │                       │                     │  8× ring/set, <0.1 ms  │                  │
   │                       │                     │                        │─── Serial TX ───▶│
   │                       │                     │                        │  Ring 0: 6.9 ms  │
   │                       │                     │                        │  Ring 1: 13.9 ms │
   │                       │                     │                        │  Ring 2: 20.8 ms │
   │                       │                     │                        │  Ring 3: 27.8 ms │
```

### Latenzbudget (nach select()-Fix)

| Segment | Dauer | Jitter |
|---------|-------|--------|
| Teletype I2C-Write → Arduino | ~0.3 ms | gering |
| Arduino Serial TX (4 Bytes) | 0.35 ms | < 0.1 ms |
| RPi Serial RX (select-wake) | < 1 ms | ± 0.5 ms |
| Main Thread wakeup (OS-Scheduler) | 1–4 ms | ± 3 ms |
| update() + display() | ~0.5 ms | < 0.2 ms |
| UDP Loopback (localhost) | < 0.1 ms | vernachlässigbar |
| serialoscd → Arc Ring 0 sichtbar | ~6.9 ms | ± 0.5 ms |
| serialoscd → Arc Ring 3 sichtbar | ~27.8 ms | ± 0.5 ms |
| **Gesamt Ring 0** | **~9–12 ms** | **± 4 ms** |
| **Gesamt Ring 3** | **~30–33 ms** | **± 4 ms** |

**Irreduzibler Ring-Spread**: 20.9 ms zwischen Ring 0 und Ring 3.  
Ursache: OSC-Befehle werden von serialoscd sequentiell über eine einzige 115200-Baud-Leitung gesendet.

---

## Vor dem select()-Fix (sleep-basiert)

| Segment | Alt (sleep) | Neu (select) |
|---------|------------|--------------|
| RPi Serial RX Latenz | ⌀ 5 ms, max 10 ms | ⌀ <1 ms, max ~1 ms |
| Gesamtjitter pro Tick | **± 10 ms** | **± 4 ms** |
| Hauptursache des Ruckelns | sleep(10ms) vor in_waiting-Check | OS-Scheduler (unvermeidlich) |

---

## Arc-Serielle Bandbreite (115200 Baud = 11.52 KB/s)

### Paketgrößen

| Pfad | Bytes | ms | Wann |
|------|-------|-----|------|
| ring/all | 32 | 2.8 | Flash-Animation (alle LEDs gleich) |
| ring/set | 40 | 3.5 | Normal/Dot (1–8 LED-Änderungen) |
| ring/all + 2× ring/set | 112 | 9.7 | Flash→Normal-Übergang (nach arc.py Fix) |
| ring/map | 348 | 30.2 | Edit-Modus-Eintritt, Moduswechsel |
| 4× ring/map (alt) | 1392 | 121 | Flash→Normal vor Fix — Hauptruckelursache |

### Auslastung bei M50 (20 Ticks/s)

| Szenario | KB/s | % Kapazität |
|----------|------|------------|
| 4 Ringe normal (2× ring/set je Ring) | 6.4 | 56 % |
| 4 Ringe Flash (ring/all) | 3.2 | 28 % |
| Peak (normal + Flash gleichzeitig) | 9.6 | **83 %** |
| Flash→Normal-Burst (alt, ring/map ×4) | Impuls 1392 B | 121 ms blockiert |
| Flash→Normal-Burst (neu, ring/all+sets) | Impuls 448 B | 39 ms |

Bei M50 läuft der Arc-Serialbus an der Grenze. Paketloss durch serialoscd-Buffering ist bei > 83 % Auslastung möglich (keine Bestätigung, UDP wird schweigend verworfen).

---

## Ring-Spread: das irreduzibler Hardware-Limit

Alle 4 Ringe reagieren auf denselben IIS 88 Tick, aber serialoscd sendet sequentiell:

```
IIS 88 empfangen
    ↓ (9 ms Gesamtpipeline)
Ring 0 sichtbar    ████ 6.9 ms
Ring 1 sichtbar    ░░░░████ 13.9 ms
Ring 2 sichtbar    ░░░░░░░░████ 20.8 ms
Ring 3 sichtbar    ░░░░░░░░░░░░████ 27.8 ms
                                ↑
                               27.8 ms Spread
```

Bei **M500** (500 ms Tick): Spread = 5.6 % der Tick-Periode → kaum wahrnehmbar.  
Bei **M50** (50 ms Tick): Spread = 55 % der Tick-Periode → deutlich sichtbar.

**Lösung existiert nicht** innerhalb des OSC/serialoscd-Protokolls. serialoscd bietet keinen Multi-Ring-Batch-Befehl. Die einzige Möglichkeit wäre, den Arc direkt über FTDI ohne serialoscd anzusprechen (direktes serielle Protokoll implementieren).

---

## IIQ-Zuverlässigkeit

### fired_until-Fenster

```python
_fired_until[i] = time.time() + _tick_interval * 1.5
```

| Tempo | Tick-Interval | Fired-Fenster | Ticks im Fenster |
|-------|--------------|---------------|-----------------|
| M50  | 50 ms | 75 ms | 1.5 ✓ |
| M100 | 100 ms | 150 ms | 1.5 ✓ |
| M500 | 500 ms | 750 ms | 1.5 ✓ |

Das Fenster ist immer genau 1.5 Ticks breit, unabhängig vom Tempo.

### TX-Pipeline zum Arduino

| Schritt | Dauer |
|---------|-------|
| IIS 88 empfangen → `_last_send = 0.0` | sofort |
| main thread wacht auf, `update_state()` baut TX-Paket | < 5 ms |
| `_rx_loop` sendet TX (nächste 40-Hz-Slot) | < 25 ms |
| Arduino erhält neues State-Paket | < 30 ms nach IIS 88 |
| Teletype liest IIQ (typisch nach 1–5 ms) | State ist aktuell |

---

## Bekannte Grenzen (nicht behebbar ohne Hardware-Änderung)

1. **Ring-Spread 28 ms**: serialoscd schreibt sequentiell. Nur mit direktem FTDI-Zugang behebbar.
2. **OS-Scheduler-Jitter 1–4 ms**: RPi A+ ist kein RTOS. Linux-Scheduler hat ~1 ms Timer-Granularität.
3. **GIL-Contention**: Single-Core RPi A+ — RX-Thread und Main-Thread wechseln sich ab. Bei hoher Last kann der Jitter auf 5–10 ms steigen.
4. **serialoscd als Black Box**: Keine Kontrolle über serialoscd's interne Latenz oder Pufferverhalten.

---

## Optimierungsverlauf

| Datum | Maßnahme | Wirkung |
|-------|---------|---------|
| – | Ausgangszustand (ring/map für alles) | 4× 348 B = 121 ms pro Tick |
| – | ring/set für Dot-Bewegung (≤8 LEDs) | 27.8 ms statt 121 ms |
| – | ring/all für Flash-Animation | 11 ms statt 121 ms pro Flash-Frame |
| – | _tick_event: main loop wacht sofort auf IIS 88 | Tick→Display: 40 ms → <5 ms |
| – | _last_send = 0 vor clock_tick() | Race-Fix: sofortige TX nach Tick |
| – | arc.py: uniform-old → ring/all+patches | Flash→Normal: 121 ms → 39 ms |
| 2026-06-20 | select() statt sleep(10ms) in _rx_loop | RX-Latenz: ⌀5 ms → ⌀<1 ms |
| 2026-06-20 | Debug-Log IIS 88 entfernt | Kein String-Alloc im Hot-Path |
