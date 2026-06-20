"""
Euclidean Rhythm Mode — Bjorklund algorithm distributes k beats over n steps
"""
import logging
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

_N_ALL        = [16, 12, 8, 5]   # default loop lengths per ring_hint
_STEP_RATE    = 4.0               # steps per second (shared default)


def _bjorklund(n: int, k: int) -> list:
    """Euclidean rhythm: k beats distributed as evenly as possible over n steps."""
    if n <= 0:
        return [0]
    k = max(0, min(k, n))
    if k == 0:
        return [0] * n
    if k >= n:
        return [1] * n
    # Bresenham/Euclidean distribution
    bucket = 0
    result = []
    for _ in range(n):
        bucket += k
        if bucket >= n:
            result.append(1)
            bucket -= n
        else:
            result.append(0)
    # Rotate so the first beat lands at step 0
    try:
        first = result.index(1)
        result = result[first:] + result[:first]
    except ValueError:
        pass
    return result


class EuclideanMode(ArcMode):
    """
    Euclidean rhythm sequencer. Encoder turn changes k (active beats).
    Playhead state and trigger-fired flag readable via IIQ.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Euclidean")
        self.num_rings = num_rings

        self.n          = [_N_ALL[(ring_hint + i) % 4] for i in range(num_rings)]
        self.k          = [max(1, self.n[i] // 4)      for i in range(num_rings)]
        self.step_rate  = [_STEP_RATE] * num_rings  # steps per second per ring

        self._patterns      = [_bjorklund(self.n[i], self.k[i]) for i in range(num_rings)]
        self._head          = [0]   * num_rings  # current step (int)
        self._head_frac     = [0.0] * num_rings  # fractional accumulator
        self._triggered      = [False] * num_rings
        self._trigger_hold   = [0]    * num_rings   # latch: keep triggered=True for N frames
        self._flash          = [0.0]  * num_rings

    # ------------------------------------------------------------------ #

    def update(self, dt: float = 0.016):
        for i in range(self.num_rings):
            if self._trigger_hold[i] > 0:
                self._trigger_hold[i] -= 1
            self._triggered[i] = self._trigger_hold[i] > 0
            if self._flash[i] > 0:
                self._flash[i] -= dt

            self._head_frac[i] += dt * self.step_rate[i]
            while self._head_frac[i] >= 1.0:
                self._head_frac[i] -= 1.0
                self._head[i] = (self._head[i] + 1) % self.n[i]
                if self._patterns[i][self._head[i]]:
                    self._trigger_hold[i] = 4
                    self._triggered[i] = True
                    self._flash[i] = 0.08

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.k[ring] = max(0, min(self.n[ring], self.k[ring] + delta))
            self._patterns[ring] = _bjorklund(self.n[ring], self.k[ring])

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self._head[ring] = 0
            self._head_frac[ring] = 0.0

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        n       = self.n[ring]
        pattern = self._patterns[ring]
        head    = self._head[ring]
        flash   = self._flash[ring] > 0

        result = []
        for step in range(n):
            led      = step * 64 // n
            is_head  = (step == head)
            is_beat  = bool(pattern[step])

            if flash and is_head:
                b = 15
            elif is_head:
                b = 12
            elif is_beat:
                b = 4
            else:
                b = 1  # grid dot

            result.append((led, b))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "STEPS" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.n[ring] = max(1, min(64, int(parts[2])))
                self.k[ring] = min(self.k[ring], self.n[ring])
                self._patterns[ring] = _bjorklund(self.n[ring], self.k[ring])
        elif cmd == "BEATS" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.k[ring] = max(0, min(self.n[ring], int(parts[2])))
                self._patterns[ring] = _bjorklund(self.n[ring], self.k[ring])
        elif cmd == "RATE" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.step_rate[ring] = max(0.1, min(64.0, float(parts[2])))
        elif cmd == "RESET":
            for i in range(self.num_rings):
                self._head[i] = 0
                self._head_frac[i] = 0.0
