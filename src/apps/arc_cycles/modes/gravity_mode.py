"""
Gravity Mode - Particles fall under gravity, bounce off edges
"""
import logging
from typing import List, Tuple
from ..physics import PhysicsEngine, Particle
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)


class GravityMode(ArcMode):
    """
    Gravity Mode - Particles fall downward (position 32 = bottom).
    Bounce off edges. Multiple particles per ring for interesting patterns.
    """

    def __init__(self, arc, num_rings: int = 4, ring_hint: int = 0):
        super().__init__(arc, "Gravity")
        self.num_rings = num_rings

        self.physics = PhysicsEngine(num_rings=num_rings)
        for ring_idx in range(num_rings):
            for i in range(4):
                particle = Particle(position=i * 16, velocity=0, mass=1.0 + i * 0.2, brightness=12)
                self.physics.rings[ring_idx][i] = particle

        self.gravity_strength = 5.0
        self.bounce_damping   = 0.7
        self.encoder_impulse  = [0] * num_rings

    def update(self, dt: float = 0.016):
        for ring_idx in range(self.num_rings):
            for particle in self.physics.rings[ring_idx]:
                delta_to_bottom = 32 - particle.position
                gravity_force = self.gravity_strength * (delta_to_bottom / 32.0)
                particle.update(gravity_force, dt)
                particle.wrap_position()
                if particle.position < 2:
                    particle.position = 2
                    particle.velocity *= -self.bounce_damping
                elif particle.position > 62:
                    particle.position = 62
                    particle.velocity *= -self.bounce_damping
                if self.encoder_impulse[ring_idx] != 0:
                    particle.velocity += self.encoder_impulse[ring_idx] / 4.0
                    self.encoder_impulse[ring_idx] *= 0.9

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.encoder_impulse[ring] = delta * 3
            # logger.debug(f"Gravity ring {ring}: impulse {delta}")

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            for i, particle in enumerate(self.physics.rings[ring]):
                particle.position = i * 16
                particle.velocity = 0
            logger.info(f"Gravity ring {ring} reset")

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        result = []
        for particle in self.physics.rings[ring]:
            pos = int(particle.position) % 64
            brightness = int(particle.brightness)
            result.append((pos, brightness))
            for glow in range(1, 3):
                gb = max(0, brightness - glow * 3)
                if gb > 0:
                    result.append(((pos + glow) % 64, gb))
                    result.append(((pos - glow) % 64, gb))
        return result

    def teletype_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "STRENGTH" and len(parts) == 2:
            self.gravity_strength = max(0, min(10, float(parts[1])))
            logger.info(f"Gravity strength: {self.gravity_strength}")
        elif cmd == "RESET":
            for ring_idx in range(self.num_rings):
                for i, particle in enumerate(self.physics.rings[ring_idx]):
                    particle.position = i * 16
                    particle.velocity = 0
            logger.info("Gravity reset")
