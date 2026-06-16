"""
Chaos Attractor Mode — Lorenz strange attractor, X coordinate projected onto ring.
"""
import logging
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

SIGMA = 10.0
BETA  = 8.0 / 3.0
RHO   = 28.0

TIME_SCALE = 0.15   # multiplier on dt before Euler integration (attractor speed)
SUBSTEPS   = 4       # Euler substeps per frame

# Initial conditions give each ring_hint a different orbit region
_INITS = [
    (0.1,  0.1,  0.1),
    (5.0, -5.0, 20.0),
    (-5.0, 5.0, 25.0),
    (3.0,  3.0, 15.0),
]

def _x_to_led(x: float) -> int:
    """Map Lorenz X (roughly −25…+25) to LED 0–63."""
    return int((x + 25.0) * 63.0 / 50.0) % 64


class ChaosMode(ArcMode):
    """
    Lorenz attractor. Encoder changes ρ (rho), shifting the attractor shape.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Chaos")
        self.num_rings = num_rings

        self.rho = [RHO] * num_rings
        self._x: list[float] = []
        self._y: list[float] = []
        self._z: list[float] = []
        for i in range(num_rings):
            xi, yi, zi = _INITS[(ring_hint + i) % 4]
            self._x.append(xi)
            self._y.append(yi)
            self._z.append(zi)

        self._trail: list[list[int]] = [[] for _ in range(num_rings)]

    # ------------------------------------------------------------------ #

    def update(self, dt: float = 0.016):
        h = dt * TIME_SCALE / SUBSTEPS
        for i in range(self.num_rings):
            x, y, z = self._x[i], self._y[i], self._z[i]
            rho = self.rho[i]
            for _ in range(SUBSTEPS):
                dx = SIGMA * (y - x)
                dy = x * (rho - z) - y
                dz = x * y - BETA * z
                x += dx * h
                y += dy * h
                z += dz * h
            self._x[i], self._y[i], self._z[i] = x, y, z

            led = _x_to_led(x)
            trail = self._trail[i]
            if not trail or trail[-1] != led:
                trail.append(led)
                if len(trail) > 5:
                    trail.pop(0)

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.rho[ring] = max(1.0, min(60.0, self.rho[ring] + delta * 0.5))

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            xi, yi, zi = _INITS[ring % 4]
            self._x[ring], self._y[ring], self._z[ring] = xi, yi, zi
            self.rho[ring] = RHO
            self._trail[ring] = []

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        trail = self._trail[ring]
        if not trail:
            return []
        result = []
        brightness = [15, 10, 6, 3, 1]
        for t, led in enumerate(reversed(trail)):
            b = brightness[t] if t < len(brightness) else 1
            result.append((led, b))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "RHO" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.rho[ring] = max(1.0, min(60.0, float(parts[2])))
        elif cmd == "RESET":
            for i in range(self.num_rings):
                self.on_encoder_press(i)
