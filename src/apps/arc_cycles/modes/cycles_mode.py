"""
Classic Cycles Mode
"""
import logging
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)


class CyclesMode(ArcMode):

    FRICTION    = 0.985  # decay per frame
    SENSITIVITY = 0.1    # positions-per-frame per encoder-tick
    MAX_SPEED   = 2.0    # hard cap so the ring never spins uncontrollably

    def __init__(self, arc, num_rings: int = 4):
        super().__init__(arc, "Cycles")
        self.num_rings = num_rings
        self.positions = [0.0] * num_rings
        self.speeds    = [0.0] * num_rings

    def update(self, dt: float = 0.016):
        for i in range(self.num_rings):
            self.speeds[i] *= self.FRICTION
            if abs(self.speeds[i]) < 0.005:
                self.speeds[i] = 0.0
            self.positions[i] = (self.positions[i] + self.speeds[i]) % 64

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.speeds[ring] += delta * self.SENSITIVITY
            self.speeds[ring] = max(-self.MAX_SPEED, min(self.MAX_SPEED, self.speeds[ring]))

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self.speeds[ring] = 0.0

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        """2 LEDs: bright head + dim tail — like Ansible Cycles."""
        pos  = int(self.positions[ring]) % 64
        tail = (pos - 1) % 64
        return [(pos, 15), (tail, 3)]

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "RESET":
            for i in range(self.num_rings):
                self.positions[i] = 0.0
                self.speeds[i] = 0.0
        elif cmd == "SPEED" and len(parts) == 3:
            ring, speed = int(parts[1]), float(parts[2])
            if 0 <= ring < self.num_rings:
                self.speeds[ring] = speed
        elif cmd == "POS" and len(parts) == 3:
            ring, pos = int(parts[1]), float(parts[2])
            if 0 <= ring < self.num_rings:
                self.positions[ring] = pos % 64
