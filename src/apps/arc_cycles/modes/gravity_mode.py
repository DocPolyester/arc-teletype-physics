"""
Gravity Mode - Particles fall under gravity, bounce off edges
"""
import logging
import math
from typing import List, Tuple
from ..physics import PhysicsEngine, Particle
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)


class GravityMode(ArcMode):
    """
    Gravity Mode - Particles fall downward (position 32 = bottom).
    Bounce off edges. Multiple particles per ring for interesting patterns.
    """
    
    def __init__(self, arc):
        super().__init__(arc, "Gravity")
        
        self.physics = PhysicsEngine(num_rings=4)
        
        # Use multiple particles per ring for richer visuals
        for ring_idx in range(4):
            for i in range(4):
                particle = Particle(
                    position=i * 16,
                    velocity=0,
                    mass=1.0 + i * 0.2,
                    brightness=12
                )
                self.physics.rings[ring_idx][i] = particle
        
        self.gravity_strength = 5.0
        self.bounce_damping = 0.7
        
        # External forces from encoders
        self.encoder_impulse = [0, 0, 0, 0]
    
    def update(self, dt: float = 0.016):
        """Apply gravity and collision physics."""
        for ring_idx in range(4):
            for particle in self.physics.rings[ring_idx]:
                # Gravity downward (toward position 32)
                delta_to_bottom = 32 - particle.position
                gravity_force = self.gravity_strength * (delta_to_bottom / 32.0)
                
                particle.update(gravity_force, dt)
                particle.wrap_position()
                
                # Bounce at edges (collision with "walls" at 0 and 64)
                if particle.position < 2:
                    particle.position = 2
                    particle.velocity *= -self.bounce_damping
                elif particle.position > 62:
                    particle.position = 62
                    particle.velocity *= -self.bounce_damping
                
                # Apply encoder impulse
                if self.encoder_impulse[ring_idx] != 0:
                    particle.velocity += self.encoder_impulse[ring_idx] / 4.0
                    self.encoder_impulse[ring_idx] *= 0.9
    
    def on_encoder_turn(self, ring: int, delta: int):
        """Encoder creates upward impulse."""
        self.encoder_impulse[ring] = delta * 3
        # logger.debug(f"Gravity ring {ring}: impulse {delta}")
    
    def on_encoder_press(self, ring: int):
        """Reset particles to top of ring."""
        for i, particle in enumerate(self.physics.rings[ring]):
            particle.position = i * 16
            particle.velocity = 0
        logger.info(f"Gravity ring {ring} reset")
    
    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        """Display particles with glow effect."""
        result = []
        
        for particle in self.physics.rings[ring]:
            pos = int(particle.position) % 64
            brightness = int(particle.brightness)
            
            # Main particle
            result.append((pos, brightness))
            
            # Glow around particle
            for glow in range(1, 3):
                glow_pos = (pos + glow) % 64
                glow_brightness = max(0, brightness - glow * 3)
                if glow_brightness > 0:
                    result.append((glow_pos, glow_brightness))
                
                glow_pos = (pos - glow) % 64
                if glow_brightness > 0:
                    result.append((glow_pos, glow_brightness))
        
        return result
    
    def teletype_command(self, command: str):
        """
        Teletype control:
        - GRAV.STRENGTH <0-10> - Set gravity strength
        - GRAV.RESET - Reset all particles
        """
        parts = command.split()
        
        if len(parts) == 0:
            return
        
        cmd = parts[0].upper()
        
        if cmd == "STRENGTH" and len(parts) == 2:
            strength = float(parts[1])
            self.gravity_strength = max(0, min(10, strength))
            logger.info(f"Gravity strength: {strength}")
        
        elif cmd == "RESET":
            for ring_idx in range(4):
                for i, particle in enumerate(self.physics.rings[ring_idx]):
                    particle.position = i * 16
                    particle.velocity = 0
            logger.info("Gravity reset")
