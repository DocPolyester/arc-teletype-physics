"""
Phase Shift — Steve Reich style.

Zwei Ringe drehen sich mit leicht unterschiedlichen Geschwindigkeiten.
Der Phasen-Offset zwischen ihnen driftet langsam, bis sie sich wieder treffen.

Ring A (rings[0]): Master — Encoder ändert Basisgeschwindigkeit
Ring B (rings[1]): Slave  — Encoder ändert Drift-Rate (wie schnell die Phase wandert)

Encoder Press (beide Ringe): Ringe neu ausrichten (Phase auf 0 zurücksetzen)
"""

from apps.arc_cycles.mode_base import MultiRingMode

SPEED_DEF   = 10.0   # LED/Sekunde Basisrotation (~6 s pro Umdrehung)
DRIFT_DEF   =  1.5   # LED/Sekunde Geschwindigkeitsdifferenz (~43 s für volle Phase)
SPEED_MIN   =  0.0
SPEED_MAX   = 30.0
DRIFT_MIN   =  0.0
DRIFT_MAX   = 10.0
SPEED_STEP  =  0.5   # Encoder-Empfindlichkeit Geschwindigkeit
DRIFT_STEP  =  0.2   # Encoder-Empfindlichkeit Drift
TRAIL       = [15, 8, 4, 2, 1]   # Helligkeit: Kopf + 4 Trail-Pixel


class PhaseShiftMode(MultiRingMode):
    """
    Steve Reich Phase Shift für ein Paar physischer Ringe.
    rings[0] = Master, rings[1] = Slave.
    """

    def __init__(self, rings: list, arc, arc_offset: int = 0, ring_hints: list = None):
        super().__init__(rings, arc, arc_offset)
        self._pos   = [0.0, 16.0]   # Startversatz damit man sofort etwas sieht
        self._speed = SPEED_DEF
        self._drift = DRIFT_DEF

    # ------------------------------------------------------------------ #

    def update(self, dt: float):
        self._pos[0] = (self._pos[0] + self._speed * dt) % 64.0
        self._pos[1] = (self._pos[1] + (self._speed + self._drift) * dt) % 64.0

    def display(self):
        phase_diff = abs(self._pos[0] - self._pos[1]) % 64
        aligned = phase_diff < 1.5 or phase_diff > 62.5

        for i, ring in enumerate(self.rings):
            leds = [0] * 64
            p = self._pos[i]
            for t, bright in enumerate(TRAIL):
                idx = int(round(p - t)) % 64
                b   = min(15, bright + (4 if aligned else 0))
                if leds[idx] < b:
                    leds[idx] = b
            self._send_ring(ring, leds)

    # ------------------------------------------------------------------ #

    def on_encoder_turn(self, ring: int, delta: int):
        if ring == self.rings[0]:
            self._speed = max(SPEED_MIN, min(SPEED_MAX, self._speed + delta * SPEED_STEP))
        elif ring == self.rings[1]:
            self._drift = max(DRIFT_MIN, min(DRIFT_MAX, self._drift + delta * DRIFT_STEP))

    def on_encoder_press(self, ring: int):
        # Beide Ringe neu ausrichten
        self._pos[0] = 0.0
        self._pos[1] = 0.0
        self._speed  = SPEED_DEF
        self._drift  = DRIFT_DEF

    def get_iiq_value(self, ring: int, vtype: int) -> int:
        if ring not in self.rings:
            return 0
        i = self.rings.index(ring)
        if vtype == 0:  # IIQ x0: Rotationsposition dieses Rings (0–5000)
            return int(self._pos[i] * 5000 / 64)
        if vtype == 1:  # IIQ x1: Phasendifferenz zwischen A und B (0–5000)
            diff = abs(self._pos[0] - self._pos[1]) % 64
            if diff > 32:
                diff = 64 - diff
            return int(diff * 5000 / 32)
        return 0
