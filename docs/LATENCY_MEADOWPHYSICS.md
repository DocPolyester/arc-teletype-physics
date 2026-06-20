# Latenz-Analyse: Meadowphysics Multi-Ring (IIS 14)

Letzte Messung: 2026-06-20  
Hardware: Raspberry Pi A+ (700 MHz, 1 Core, ARMv6) · Arduino Nano V3.0 · Monome Arc 4 · Monome Teletype  
Firmware: teletype_bridge.ino v2.2 · middleware v2.x

---

## Gemessene Latenzen (SSH-Messskript)

Messung auf `/dev/ttyUSB1` bei Teletype M100 (52 IIS-88-Pakete):

| Kennzahl | RPi RX→TX Latenz | IIS-88-Abstände |
|----------|-----------------|-----------------|
| Min      | 2.60 ms         | 90.09 ms        |
| Median   | 3.99 ms         | 99.87 ms        |
| Mean     | 5.16 ms         | —               |
| P95      | 12.55 ms        | —               |
| Max      | 14.87 ms        | —               |
| Stdev    | 2.95 ms         | —               |

**RX→TX Latenz** = Zeit von `select()` wacht auf (IIS-88-Bytes im Kernel-Buffer) bis `ser.write()` abgeschlossen.  
Der Median von ~4 ms setzt sich zusammen aus:
- USB Full-Speed Polling-Overhead (write an FTDI-Chip): ~1–2 ms
- Python State-Machine + Systemaufruf-Overhead: ~0.3 ms
- 34-Byte UART-Übertragung zum Arduino: **2.95 ms** (festes physikalisches Limit)

---

## Warum Teletype IIQ sporadisch 0 zurückliefert

### Vollständige Signalkette: IIS 88 → ring_vals aktuell

```
Teletype          Arduino                RPi A+             Arduino (ring_vals)
    │                 │                    │                       │
    │── I2C Write ───▶│                    │                       │
    │  IIS 88 (0x58)  │                    │                       │
    │   ~0.3 ms       │── USB-Serial ─────▶│                       │
    │                 │  [BB 01 58 59]     │                       │
    │                 │  ~1.0 ms USB       │                       │
    │                 │                    │ select() wacht         │
    │                 │                    │ Python parst ~0.3ms    │
    │                 │                    │── ser.write(34B) ─────▶│
    │                 │                    │  ~1–2ms USB write      │
    │                 │                    │                        │ erste 2 Bytes
    │                 │                    │                        │ ring_vals[0][0] ✓
    │                 │                    │                        │ +0.17ms
    │                 │                    │                        │ ring_vals[1][0] ✓
    │                 │                    │                        │ +0.87ms
    │                 │                    │                        │ ring_vals[2][0] ✓
    │                 │                    │                        │ +1.56ms
    │                 │                    │                        │ ring_vals[3][0] ✓
    │                 │                    │                        │ +2.26ms
    │                 │                    │                          ↕ 2.95ms Draht gesamt
    │
    │── IIQ 20 ───────────────────────────▶│ onRequest()
    │   I2C Read       0.8 ms nach IIS 88  │  liest ring_vals[0][0]
    │── IIQ 30 ────────────────────────────│ 2.0 ms nach IIS 88
    │── IIQ 40 ────────────────────────────│ 3.2 ms nach IIS 88
    │── IIQ 50 ────────────────────────────│ 4.4 ms nach IIS 88
```

### Timing-Budget

| | ring_vals bereit (P50) | ring_vals bereit (P95) | Teletype liest IIQ |
|---|---|---|---|
| Ring 0 | ~3.5 ms | ~12 ms | ~0.8 ms |
| Ring 1 | ~4.2 ms | ~13 ms | ~2.0 ms |
| Ring 2 | ~5.0 ms | ~14 ms | ~3.2 ms |
| Ring 3 | ~5.8 ms | ~15 ms | ~4.4 ms |

**Ergebnis: ring_vals ist bei JEDEM IIQ-Read noch veraltet** (Median ~4ms Latenz vs. IIQ bei 0.8–4.4ms).

### Warum Ring 0 trotzdem meistens funktioniert

`ring_vals[0][0]` enthält den Wert vom **vorherigen Tick**. Wenn Ring 0 jede Runde feuert (Periode = 1 oder sehr kurz), war `ring_vals[0][0] = 5000` schon beim letzten TX-Update gesetzt. Die Antwort ist korrekt — aber aus der vorigen Runde.

Ringe mit längerer Periode feuern nicht jede Runde. Wenn Ring 2 in Tick N feuert, aber in Tick N-1 nicht gefeuert hat, steht `ring_vals[2][0] = 0` in den veralteten Daten → IIQ 40 gibt 0 zurück obwohl der Flash sichtbar ist.

### Warum Encoder-Drehung die Aussetzer verschlimmert

Beim Encoder-Drehen sendet serialoscd ring/map-Pakete (Edit-Modus: 348 Bytes × 4 Ringe = 1392 Bytes über USB). Arc und Arduino teilen denselben USB-Hub. Schwere USB-Last auf `/dev/ttyUSB0` (Arc) verzögert den USB-Transfer auf `/dev/ttyUSB1` (Arduino). Die RX→TX-Latenz steigt von ~4ms auf ~10–15ms. Die Aussetzer häufen sich.

---

## Optimierungsverlauf

| Maßnahme | Effekt |
|---------|--------|
| v2.0: single slot, IIQ forward | IIQ belegte Slot → IIS 88 verloren |
| v2.1: Circular Queue + IIQ-Filter | Keine IIQ-Drops mehr, saubere TX-Pakete |
| select() statt sleep(10ms) | RX-Wake-Latenz: ~5ms → <1ms |
| IIS 88 sofortiger TX (arduino-rx Thread) | Kein 25ms Hauptthread-Umweg |
| v2.2: Progressives ring_vals[r][0] Update | ring_vals[r][0] früher bereit (innerhalb TX-Paket) |
| Double-TX Fix (RX vor TX in _rx_loop) | Kein USART-Buffer-Overflow (68B > 64B) mehr |

---

## Grundsätzliche Grenzen (nicht behebbar ohne Hardware-Änderung)

1. **IIQ liest stets veralteten State**: Teletype liest IIQ 0.8–4.4ms nach IIS 88. RPi braucht median 4ms + 2.95ms Draht = ~7ms um ring_vals zu aktualisieren. Die Lücke ist fundamental.

2. **USB-Hub-Bottleneck**: Arc und Arduino teilen einen USB-FS-Hub. USB Full Speed Polling-Latenz = 1ms, bei Konflikt mehr.

3. **OS-Scheduler-Jitter**: RPi A+ ist kein RTOS. Linux-Scheduler hat ~1ms Timer-Granularität; P95 der RX→TX-Latenz liegt bei 12.5ms.

4. **serialoscd Black Box**: ring/map unter Encoder-Last (1392 Bytes) sättigt den USB-Hub und erhöht die Arduino-Serial-Latenz.

---

## Workaround-Empfehlung für Teletype-Skripte

IIQ im **nächsten** METRO-Zyklus lesen statt im gleichen:

```
; METRO M100 Skript:
IIS 49 88       ; Tick auslösen
                ; ring_vals jetzt noch vom letzten Tick
IIQ 49 20 → A  ; liest den State des VORHERIGEN Ticks
```

Oder mit DEL:

```
IIS 49 88
DEL 8           ; 8ms warten → ring_vals wurde aktualisiert
IIQ 49 20 → A  ; liest aktuellen State
```

Bei M100 (10 Hz) sind 8ms DEL = 8% des Tick-Abstands. Musikalisch kaum hörbar, löst aber den Timing-Konflikt zuverlässig.

---

## Messskript

```bash
# Middleware stoppen, dann:
ssh seek@monome-arc.local \
  "python3 ~/arc-middleware/scripts/measure_latency.py 30"
```
