"""
Meadowphysics  (IIS 14)

Vier unabhängige Countdown-Zähler, je einer pro Ring.
Jeder Ring feuert eigenständig wenn sein Zähler die eingestellte Periode erreicht.
Kein Kaskaden-Reset — alle Ringe sind vollständig unabhängig.

Reset aller Ringe: IIS 89

Display (Normal):
  Heller Punkt + Trail  = aktuelle Position (sub-tick interpoliert)
  Heller Blitz          = Ring hat gefeuert
  Pip bei LED 0         = Fire-Punkt (12 Uhr)

Display (Edit, 1.5 s nach Encoder-Drehung):
  Gefüllter Bogen       = Sektor von Startpunkt bis LED 0
  Startpunkt + Endpunkt heller
  Heller Punkt          = aktueller Schritt im Bogen

Encoder:
  Turn links  : Periode verlängern (Startpunkt wandert zurück)
  Turn rechts : Periode verkürzen
  Press       : Diesen Ring manuell zurücksetzen
"""

import time
from apps.arc_cycles.mode_base import MultiRingMode

_CLOCK_RATE     = 4.0
_MIN_PERIOD     = 2
_MAX_PERIOD     = 64
_FLASH_DUR      = 0.30
_TRAIL_LEN      = 5
_ENC_DIV        = 3
_EDIT_DUR       = 1.5    # Sekunden Step-Grid-Anzeige nach Encoder-Drehung
_DEFAULTS       = [32, 16, 8, 4]


class MeadowphysicsMode(MultiRingMode):

    def __init__(self, rings: list, arc, arc_offset: int = 0, **kw):
        super().__init__(rings, arc, arc_offset)
        n = len(rings)
        self._period        = [_DEFAULTS[i % len(_DEFAULTS)] for i in range(n)]
        self._count         = [0] * n
        self._flash         = [0.0] * n
        self._edit_timer    = [0.0] * n
        self._fired         = [False] * n
        self._fired_hold    = [0] * n
        self._acc           = 0.0
        self._use_int_clk   = True
        self._enc_acc       = [0] * n
        self._last_tick     = time.time()   # für sub-tick Interpolation

    # ------------------------------------------------------------------ #

    def on_clock_tick(self):
        self._use_int_clk = False
        self._do_step()

    def _do_step(self):
        self._last_tick = time.time()
        for i in range(len(self.rings)):
            self._count[i] += 1
            if self._count[i] >= self._period[i]:
                self._fire(i)

    def _fire(self, i: int):
        self._fired_hold[i] = 4
        self._fired[i]      = True
        self._flash[i]      = _FLASH_DUR
        self._count[i]      = 0

    def reset_all(self):
        """IIS 89 — alle Ringe auf Startposition zurücksetzen."""
        for i in range(len(self.rings)):
            self._count[i]      = 0
            self._flash[i]      = 0.0
            self._edit_timer[i] = 0.0
            self._fired[i]      = False
            self._fired_hold[i] = 0

    def update(self, dt: float):
        for i in range(len(self.rings)):
            if self._fired_hold[i] > 0:
                self._fired_hold[i] -= 1
            self._fired[i] = self._fired_hold[i] > 0
            if self._flash[i]      > 0: self._flash[i]      = max(0.0, self._flash[i]      - dt)
            if self._edit_timer[i] > 0: self._edit_timer[i] = max(0.0, self._edit_timer[i] - dt)

        if self._use_int_clk:
            self._acc += dt * _CLOCK_RATE
            while self._acc >= 1.0:
                self._acc -= 1.0
                self._do_step()

    # ------------------------------------------------------------------ #

    def display(self):
        now      = time.time()
        # Fraction elapsed since last tick (0..1) — used for smooth interpolation
        tick_frac = min(1.0, (now - self._last_tick) * _CLOCK_RATE)

        for i, ring in enumerate(self.rings):
            leds   = [1] * 64
            period = self._period[i]
            count  = self._count[i]

            if self._flash[i] > 0:
                # Heller Self-Fire-Blitz (fade)
                fade = max(1, int(15 * self._flash[i] / _FLASH_DUR))
                leds = [fade] * 64

            elif self._edit_timer[i] > 0:
                # ── Sektor-Modus ─────────────────────────────────────────
                # Bogen von Startpunkt (64-period) bis LED 63, feuert bei LED 0
                start = (64 - period) % 64
                for step in range(period):
                    leds[(start + step) % 64] = 7
                leds[0]     = 13        # Fire-Punkt (12 Uhr)
                leds[start] = 11        # Loslaufpunkt
                leds[(start + min(count, period - 1)) % 64] = 15

            else:
                # ── Normal-Modus ──────────────────────────────────────────
                # Dot läuft von (64-period) bis 63, feuert bei LED 0
                start = (64 - period) % 64
                smooth_count = count + tick_frac
                pos = int(start + smooth_count) % 64
                for t in range(_TRAIL_LEN, 0, -1):
                    leds[(pos - t) % 64] = max(leds[(pos - t) % 64], t + 1)
                leds[pos] = 15
                leds[0]   = max(leds[0], 4)   # Fire-Punkt immer sichtbar

            self._send_ring(ring, leds)

    # ------------------------------------------------------------------ #

    def on_encoder_turn(self, ring: int, delta: int):
        i = self.rings.index(ring)
        self._enc_acc[i] -= delta   # links/gg uhr = länger, rechts/mit uhr = kürzer
        steps = int(self._enc_acc[i] / _ENC_DIV)
        if steps:
            self._enc_acc[i] -= steps * _ENC_DIV
            self._period[i] = max(_MIN_PERIOD, min(_MAX_PERIOD, self._period[i] + steps))
            self._edit_timer[i] = _EDIT_DUR

    def on_encoder_press(self, ring: int):
        i = self.rings.index(ring)
        self._count[i]         = 0
        self._flash[i]         = 0.0
        self._cascade_flash[i] = 0.0
        self._edit_timer[i]    = 0.0

    def get_iiq_value(self, ring: int, vtype: int) -> int:
        if ring not in self.rings:
            return 0
        i = self.rings.index(ring)
        if vtype == 0:
            return 5000 if self._fired[i] else 0
        if vtype == 1:
            return self._count[i] * 5000 // max(1, self._period[i])
        return 0
