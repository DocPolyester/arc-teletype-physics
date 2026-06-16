"""
Drunk Walk Mode — Brownian motion along the ring, soft boundary reflection.
"""
import logging
import random
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

STEP_INTERVAL = 0.15   # seconds between random steps
STEP_SIZE_DEF = 2.0    # LED positions per step (encoder-adjustable)
WALL_LO = 0
WALL_HI = 63


class DrunkMode(ArcMode):
    """
    Random walk that wanders ±step_size every STEP_INTERVAL seconds.
    Reflects at walls. Encoder changes step size.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Drunk")
        self.num_rings = num_rings

        # Start spread across the ring for visual variety
        _starts = [16, 32, 48, 8]
        self.position  = [float(_starts[(ring_hint + i) % 4]) for i in range(num_rings)]
        self.step_size = [STEP_SIZE_DEF] * num_rings
        self._timer    = [random.uniform(0, STEP_INTERVAL) for _ in range(num_rings)]
        self._last_dir = [1] * num_rings

    # ------------------------------------------------------------------ #

    def update(self, dt: float = 0.016):
        for i in range(self.num_rings):
            self._timer[i] -= dt
            if self._timer[i] <= 0:
                self._timer[i] = STEP_INTERVAL
                direction = random.choice([-1, 1])
                self._last_dir[i] = direction
                self.position[i] += direction * self.step_size[i]
                # Soft wall: reflect
                if self.position[i] < WALL_LO:
                    self.position[i] = WALL_LO + (WALL_LO - self.position[i])
                    self._last_dir[i] = 1
                elif self.position[i] > WALL_HI:
                    self.position[i] = WALL_HI - (self.position[i] - WALL_HI)
                    self._last_dir[i] = -1
                self.position[i] = max(float(WALL_LO), min(float(WALL_HI), self.position[i]))

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.step_size[ring] = max(0.5, min(16.0, self.step_size[ring] + delta * 0.5))

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self.position[ring] = 32.0
            self.step_size[ring] = STEP_SIZE_DEF

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        pos = int(round(self.position[ring])) % 64
        result = [(pos, 14)]
        # faint trail
        step = self._last_dir[ring]
        for t, b in enumerate([5, 3, 1]):
            trail = (pos - step * (t + 1)) % 64
            result.append((trail, b))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "STEP" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.step_size[ring] = max(0.5, min(16.0, float(parts[2])))
        elif cmd == "RESET":
            for i in range(self.num_rings):
                self.position[i] = 32.0
