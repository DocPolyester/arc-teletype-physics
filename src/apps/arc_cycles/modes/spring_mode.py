"""
Spring/Resonator Mode - Spring mechanics with resonance effects
"""
import logging
import math
from typing import List, Tuple
from ..physics import PhysicsEngine, Particle
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)

_K_ALL = [2.0, 2.2, 1.8, 2.0]


class SpringMode(ArcMode):
    """
    Spring/Resonator Mode - Particles attracted to center with spring-like behavior.
    Resonates when encoders are turned, creating harmonic patterns.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Spring")
        self.num_rings = num_rings

        self.physics = PhysicsEngine(num_rings=num_rings)
        for ring_idx in range(num_rings):
            for i in range(4):
                particle = Particle(position=i * 16, velocity=0, mass=1.0, brightness=10)
                self.physics.rings[ring_idx][i] = particle

        self.spring_constant  = [_K_ALL[(ring_hint + i) % 4] for i in range(num_rings)]
        self.centers          = [32] * num_rings
        self.damping          = 0.92
        self.resonance        = [0.0] * num_rings
        self.resonance_decay  = 0.95

    def update(self, dt: float = 0.016):
        for ring_idx in range(self.num_rings):
            self.resonance[ring_idx] *= self.resonance_decay
            for particle in self.physics.rings[ring_idx]:
                delta = self.centers[ring_idx] - particle.position
                if delta > 32:
                    delta -= 64
                elif delta < -32:
                    delta += 64
                force = self.spring_constant[ring_idx] * delta
                force += self.resonance[ring_idx] * math.sin(particle.position / 10)
                particle.update(force, dt)
                particle.velocity *= self.damping
                particle.wrap_position()

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.resonance[ring] = min(self.resonance[ring] + abs(delta) * 0.5, 5.0)
            # logger.debug(f"Spring ring {ring}: resonance += {delta * 0.5}")

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            for particle in self.physics.rings[ring]:
                particle.position = self.centers[ring]
                particle.velocity = 0
            self.resonance[ring] = 0
            logger.info(f"Spring ring {ring} centered")

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        result = [(int(self.centers[ring]) % 64, 3)]
        for particle in self.physics.rings[ring]:
            pos = int(particle.position) % 64
            brightness = min(15, int(particle.brightness + self.resonance[ring] * 2))
            if brightness > 0:
                result.append((pos, brightness))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "K" and len(parts) == 3:
            ring = int(parts[1])
            if 0 <= ring < self.num_rings:
                self.spring_constant[ring] = max(0.1, min(5.0, float(parts[2])))
                logger.info(f"Spring ring {ring}: k = {self.spring_constant[ring]}")
        elif cmd == "CENTER" and len(parts) == 3:
            ring = int(parts[1])
            center = int(parts[2])
            if 0 <= ring < self.num_rings and 0 <= center < 64:
                self.centers[ring] = center
                logger.info(f"Spring ring {ring}: center = {center}")
        elif cmd == "RESET":
            for ring_idx in range(self.num_rings):
                self.resonance[ring_idx] = 0
                for particle in self.physics.rings[ring_idx]:
                    particle.position = self.centers[ring_idx]
                    particle.velocity = 0
            logger.info("Spring reset")
