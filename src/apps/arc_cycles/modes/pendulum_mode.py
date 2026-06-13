"""
Pendulum Mode - Physics simulation with gravity and oscillation
"""
import math
import logging
from typing import List, Tuple
from ..physics import PhysicsEngine, Particle
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

_PERIODS_ALL   = [1.0, 1.5, 2.0, 2.5]
_PHASE_ALL     = [0, math.pi / 2, math.pi, 3 * math.pi / 2]


class PendulumMode(ArcMode):
    """
    Pendulum Mode - Pendulums oscillating under gravity.
    Each ring is an independent pendulum with a different period.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Pendulum")
        self.num_rings = num_rings

        self.physics = PhysicsEngine(num_rings=num_rings)
        self.time = 0.0

        self.periods    = [_PERIODS_ALL[(ring_hint + i) % 4] for i in range(num_rings)]
        self.amplitudes = [16] * num_rings
        self.centers    = [32] * num_rings
        self.encoder_force = [0] * num_rings

    def update(self, dt: float = 0.016):
        self.time += dt
        for ring_idx in range(self.num_rings):
            omega = 2 * math.pi / self.periods[ring_idx]
            angle = omega * self.time
            phase_offset = _PHASE_ALL[ring_idx % 4]
            equilibrium = self.centers[ring_idx] + self.amplitudes[ring_idx] * math.sin(angle + phase_offset)
            particle = self.physics.rings[ring_idx][0]
            particle.position = equilibrium
            if self.encoder_force[ring_idx] != 0:
                particle.velocity += self.encoder_force[ring_idx]
                self.encoder_force[ring_idx] *= 0.9

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.encoder_force[ring] = delta * 2
            # logger.debug(f"Pendulum ring {ring}: impulse {delta}")

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self.physics.rings[ring][0].position = self.centers[ring]
            self.physics.rings[ring][0].velocity = 0
            logger.info(f"Pendulum ring {ring} reset")

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        result = []
        particle = self.physics.rings[ring][0]
        pos = int(particle.position) % 64
        result.append((pos, 14))
        for trail in range(1, 4):
            tb = max(0, 6 - trail * 2)
            if tb > 0:
                result.append(((pos - trail) % 64, tb))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "PERIOD" and len(parts) == 3:
            ring = int(parts[1])
            period_ms = int(parts[2])
            if 0 <= ring < self.num_rings:
                self.periods[ring] = period_ms / 1000.0
                logger.info(f"Ring {ring} period: {period_ms}ms")
        elif cmd == "AMP" and len(parts) == 3:
            ring = int(parts[1])
            amp = int(parts[2])
            if 0 <= ring < self.num_rings and 0 <= amp <= 32:
                self.amplitudes[ring] = amp
                logger.info(f"Ring {ring} amplitude: {amp}")
        elif cmd == "RESET":
            self.time = 0
            logger.info("Pendulum reset")
