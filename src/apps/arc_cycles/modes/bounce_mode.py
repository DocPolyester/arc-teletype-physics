"""
Bouncing Ball Rhythm Mode — ball thrown upward falls under gravity, bounces with energy loss.
"""
import logging
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

GRAVITY      = 50.0   # LED/s² — downward acceleration toward position 0
ELASTICITY   = 0.72   # velocity multiplier on each bounce
THROW_SCALE  = 20.0   # LED/s added per encoder tick (upward)
FLOOR        = 0      # bounce floor (LED position)
CEILING      = 63     # bounce ceiling

_INIT_VEL_ALL = [40.0, 48.0, 56.0, 32.0]  # initial upward velocity per ring_hint


class BounceMode(ArcMode):
    """
    Simulated ball under gravity. Encoder throws the ball upward.
    Each bounce fires a gate (readable via IIQ state 2).
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Bounce")
        self.num_rings = num_rings

        self.position = [float(FLOOR)] * num_rings
        self.velocity = [_INIT_VEL_ALL[(ring_hint + i) % 4] for i in range(num_rings)]
        self._bounced = [False] * num_rings
        self._flash   = [0.0]  * num_rings

    # ------------------------------------------------------------------ #

    def update(self, dt: float = 0.016):
        for i in range(self.num_rings):
            self._bounced[i] = False
            if self._flash[i] > 0:
                self._flash[i] -= dt

            self.velocity[i] -= GRAVITY * dt
            self.position[i] += self.velocity[i] * dt

            if self.position[i] <= FLOOR:
                self.position[i] = float(FLOOR)
                self.velocity[i] = abs(self.velocity[i]) * ELASTICITY
                if self.velocity[i] < 0.5:
                    self.velocity[i] = 0.0
                self._bounced[i] = True
                self._flash[i]   = 0.06

            elif self.position[i] >= CEILING:
                self.position[i] = float(CEILING)
                self.velocity[i] = -abs(self.velocity[i]) * ELASTICITY

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.velocity[ring] += delta * THROW_SCALE

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self.position[ring] = float(FLOOR)
            self.velocity[ring] = _INIT_VEL_ALL[ring % 4]
            self._bounced[ring] = False

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        pos   = int(round(self.position[ring])) % 64
        flash = self._flash[ring] > 0
        result = [(pos, 15 if flash else 12)]
        # short trail in the direction of movement
        vel = self.velocity[ring]
        step = -1 if vel >= 0 else 1
        for t, b in enumerate([7, 4, 2]):
            trail = (pos + step * (t + 1)) % 64
            result.append((trail, b))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "THROW" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.velocity[ring] = float(parts[2])
        elif cmd == "RESET":
            for i in range(self.num_rings):
                self.position[i] = float(FLOOR)
                self.velocity[i] = _INIT_VEL_ALL[i % 4]
