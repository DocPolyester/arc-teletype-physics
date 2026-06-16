"""
Meadowphysics  (IIS 14)

Vier unabhängige Countdown-Zähler, je einer pro Ring.
Wenn ein Ring feuert, wird der nächste Ring zusätzlich zurückgesetzt
(Kaskaden-Netzwerk: Ring 0 → Ring 1 → Ring 2 → Ring 3).

Display:
  Füllender Bogen = Fortschritt zum nächsten Fire-Event
  Voller Ring     = Fire (kurzer Flash)
  Kleiner Pip bei 0 = Referenzpunkt

Encoder:
  Turn  : Period dieses Rings ändern (2–32 Schritte)
  Press : Diesen Zähler manuell zurücksetzen (= Force Reset)

IIQ:
  State 1 von Ring N : Feuerte dieser Ring diesen Frame? (5000 = ja)
  State 0 von Ring N : Aktueller Füllstand (0–5000)

Kaskade (fest):
  Ring 0 feuert → Reset Ring 1
  Ring 1 feuert → Reset Ring 2
  Ring 2 feuert → Reset Ring 3
  Ring 3 feuert → kein weiterer Kaskaden-Reset
"""

from apps.arc_cycles.mode_base import MultiRingMode

_CLOCK_RATE  = 4.0     # Ticks pro Sekunde
_MIN_PERIOD  = 2
_MAX_PERIOD  = 32
_FLASH_DUR   = 0.12    # Sekunden Blitz-Dauer beim Feuern
_DEFAULTS    = [4, 6, 8, 12]   # verschiedene Startperioden


class MeadowphysicsMode(MultiRingMode):
    """
    Rhizomatisches Zähler-Netzwerk über alle 4 Ringe.
    """

    def __init__(self, rings: list, arc, arc_offset: int = 0, **kw):
        super().__init__(rings, arc, arc_offset)
        n = len(rings)
        self._period = [_DEFAULTS[i % len(_DEFAULTS)] for i in range(n)]
        self._count  = [0] * n
        self._flash  = [0.0] * n
        self._fired  = [False] * n
        self._acc    = 0.0

    # ------------------------------------------------------------------ #

    def _fire(self, i: int):
        self._fired[i] = True
        self._flash[i] = _FLASH_DUR
        self._count[i] = 0
        # Kaskade: nächsten Ring zurücksetzen
        n = len(self.rings)
        if i < n - 1:
            self._count[i + 1] = 0

    def update(self, dt: float):
        # Flash-Timer herunterzählen
        for i in range(len(self.rings)):
            self._fired[i] = False
            if self._flash[i] > 0:
                self._flash[i] = max(0.0, self._flash[i] - dt)

        # Clock-Tick
        self._acc += dt * _CLOCK_RATE
        while self._acc >= 1.0:
            self._acc -= 1.0
            for i in range(len(self.rings)):
                self._count[i] += 1
                if self._count[i] >= self._period[i]:
                    self._fire(i)

    # ------------------------------------------------------------------ #

    def display(self):
        for i, ring in enumerate(self.rings):
            leds = [0] * 64

            if self._flash[i] > 0:
                # Flash: alles hell
                fade = int(15 * self._flash[i] / _FLASH_DUR)
                for l in range(64):
                    leds[l] = max(1, fade)
            else:
                # Füllender Bogen
                filled = self._count[i] * 64 // max(1, self._period[i])
                for l in range(filled):
                    leds[l] = 10
                for l in range(filled, 64):
                    leds[l] = 1
                # Pip bei 0 immer sichtbar
                leds[0] = max(leds[0], 4)

            self._send_ring(ring, leds)

    # ------------------------------------------------------------------ #

    def on_encoder_turn(self, ring: int, delta: int):
        i = self.rings.index(ring)
        self._period[i] = max(_MIN_PERIOD, min(_MAX_PERIOD, self._period[i] + delta))

    def on_encoder_press(self, ring: int):
        i = self.rings.index(ring)
        self._count[i] = 0
        self._flash[i] = 0.0

    def get_iiq_value(self, ring: int, vtype: int) -> int:
        if ring not in self.rings:
            return 0
        i = self.rings.index(ring)
        if vtype == 0:  # IIQ x0: fired this tick (trigger)
            return 5000 if self._fired[i] else 0
        if vtype == 1:  # IIQ x1: Füllstand 0–5000
            return self._count[i] * 5000 // max(1, self._period[i])
        return 0
