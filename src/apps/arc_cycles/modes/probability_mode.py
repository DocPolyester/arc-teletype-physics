"""
Probability Gate Mode — Bernoulli trigger: each clock tick fires with probability p.
"""
import logging
import random
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

GATE_RATE     = 2.0    # internal clock ticks per second
PROB_STEP     = 0.02   # probability change per encoder tick
FLASH_DURATION = 0.08  # seconds the ring lights up after a trigger fires


class ProbabilityMode(ArcMode):
    """
    Filled arc display shows 0–100% probability.
    Each internal tick the gate fires with that probability.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Probability")
        self.num_rings = num_rings

        # Different starting probabilities per ring for variety
        _starts = [0.5, 0.25, 0.75, 0.33]
        self.probability = [_starts[(ring_hint + i) % 4] for i in range(num_rings)]
        self._clock_acc  = [0.0] * num_rings
        self._fired      = [False] * num_rings
        self._fired_hold = [0]   * num_rings   # latch: keep fired=True for N frames
        self._flash      = [0.0] * num_rings

    # ------------------------------------------------------------------ #

    def update(self, dt: float = 0.016):
        interval = 1.0 / GATE_RATE
        for i in range(self.num_rings):
            if self._fired_hold[i] > 0:
                self._fired_hold[i] -= 1
            self._fired[i] = self._fired_hold[i] > 0
            if self._flash[i] > 0:
                self._flash[i] -= dt

            self._clock_acc[i] += dt
            if self._clock_acc[i] >= interval:
                self._clock_acc[i] -= interval
                if random.random() < self.probability[i]:
                    self._fired_hold[i] = 4
                    self._fired[i] = True
                    self._flash[i] = FLASH_DURATION

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.probability[ring] = max(0.0, min(1.0,
                self.probability[ring] + delta * PROB_STEP))

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self.probability[ring] = 0.5
            self._flash[ring] = 0.0

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        prob  = self.probability[ring]
        flash = self._flash[ring] > 0
        filled = int(round(prob * 63))

        result = []
        if flash:
            for led in range(64):
                result.append((led, 15))
        else:
            for led in range(64):
                if led <= filled:
                    result.append((led, 8))
                else:
                    result.append((led, 1))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "PROB" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.probability[ring] = max(0.0, min(1.0, float(parts[2])))
        elif cmd == "RATE" and len(parts) == 2:
            # global rate change
            pass  # intentionally not exposed; rate is a constant
        elif cmd == "RESET":
            for i in range(self.num_rings):
                self.probability[i] = 0.5
