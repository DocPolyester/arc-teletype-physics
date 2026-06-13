"""
Orbit Mode - Orbital mechanics simulation
"""
import logging
import math
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

_RADII_ALL   = [12, 16, 20, 24]
_PERIODS_ALL = [1.0, 1.5, 2.0, 1.2]
_COUNTS_ALL  = [3, 3, 4, 4]


class OrbitMode(ArcMode):
    """
    Orbit Mode - Particles orbit around a central point.
    Multiple particles create complex orbital patterns.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Orbit")
        self.num_rings = num_rings
        self.time = 0.0

        self.radii            = [_RADII_ALL[(ring_hint + i) % 4]   for i in range(num_rings)]
        self.periods          = [_PERIODS_ALL[(ring_hint + i) % 4] for i in range(num_rings)]
        self.particle_counts  = [_COUNTS_ALL[(ring_hint + i) % 4]  for i in range(num_rings)]
        self.centers          = [32] * num_rings
        self.angular_velocities = [0.0] * num_rings
        self.ang_accel        = [0.0] * num_rings

    def update(self, dt: float = 0.016):
        self.time += dt
        for ring_idx in range(self.num_rings):
            self.angular_velocities[ring_idx] += self.ang_accel[ring_idx]
            self.angular_velocities[ring_idx] *= 0.98
            self.ang_accel[ring_idx] *= 0.95

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.ang_accel[ring] += delta * 0.3
            # logger.debug(f"Orbit ring {ring}: angular accel += {delta * 0.3}")

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self.angular_velocities[ring] = 0
            self.ang_accel[ring] = 0
            logger.info(f"Orbit ring {ring} reset")

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        result = [(int(self.centers[ring]) % 64, 2)]
        num_particles = self.particle_counts[ring]
        period        = self.periods[ring]
        radius        = self.radii[ring]
        for particle_idx in range(num_particles):
            phase_offset = particle_idx * 2 * math.pi / num_particles
            angular_vel  = 2 * math.pi / period + self.angular_velocities[ring]
            angle = angular_vel * self.time + phase_offset
            pos   = (self.centers[ring] + radius * math.sin(angle)) % 64
            brightness = max(1, min(15, int(8 + 4 * math.cos(angle))))
            result.append((int(pos), brightness))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "PERIOD" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.periods[ring] = int(parts[2]) / 1000.0
                logger.info(f"Orbit ring {ring}: period = {parts[2]}ms")
        elif cmd == "RADIUS" and len(parts) == 3:
            ring   = int(parts[1])
            radius = int(parts[2])
            if 0 <= ring < self.num_rings and 0 <= radius <= 32:
                self.radii[ring] = radius
                logger.info(f"Orbit ring {ring}: radius = {radius}")
        elif cmd == "PARTICLES" and len(parts) == 3:
            ring  = int(parts[1])
            count = max(1, min(8, int(parts[2])))
            if 0 <= ring < self.num_rings:
                self.particle_counts[ring] = count
                logger.info(f"Orbit ring {ring}: {count} particles")
        elif cmd == "RESET":
            for ring_idx in range(self.num_rings):
                self.angular_velocities[ring_idx] = 0
                self.ang_accel[ring_idx] = 0
