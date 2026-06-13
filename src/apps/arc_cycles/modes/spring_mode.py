"""
Spring/Resonator Mode - Federmechanik mit Resonanz-Effekten
"""
import logging
import math
from typing import List, Tuple
from ..physics import PhysicsEngine, Particle
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)


class SpringMode(ArcMode):
    """
    Spring/Resonator Mode - Particles attracted to center with spring-like behavior.
    Resonates when encoders are turned, creating harmonic patterns.
    """
    
    def __init__(self, arc):
        super().__init__(arc, "Spring")
        
        self.physics = PhysicsEngine(num_rings=4)
        
        # Setup particles for resonance
        for ring_idx in range(4):
            for i in range(4):
                # Distribute particles around center
                pos = i * 16
                particle = Particle(
                    position=pos,
                    velocity=0,
                    mass=1.0,
                    brightness=10
                )
                self.physics.rings[ring_idx][i] = particle
        
        # Spring parameters per ring
        self.spring_constant = [2.0, 2.2, 1.8, 2.0]  # Stiffness
        self.centers = [32, 32, 32, 32]               # Equilibrium
        self.damping = 0.92                            # Energy loss
        
        # Resonance state
        self.resonance = [0, 0, 0, 0]                 # Current resonance energy
        self.resonance_decay = 0.95
    
    def update(self, dt: float = 0.016):
        """Apply spring forces with resonance."""
        for ring_idx in range(4):
            # Decay resonance
            self.resonance[ring_idx] *= self.resonance_decay
            
            for particle in self.physics.rings[ring_idx]:
                # Spring force toward center
                delta = self.centers[ring_idx] - particle.position
                
                # Shortest path on ring
                if delta > 32:
                    delta -= 64
                elif delta < -32:
                    delta += 64
                
                force = self.spring_constant[ring_idx] * delta
                
                # Add resonance-based oscillation
                force += self.resonance[ring_idx] * math.sin(particle.position / 10)
                
                particle.update(force, dt)
                particle.velocity *= self.damping
                particle.wrap_position()
    
    def on_encoder_turn(self, ring: int, delta: int):
        """Encoder turn excites resonance."""
        # Energy transfer to resonance
        self.resonance[ring] += abs(delta) * 0.5
        self.resonance[ring] = min(self.resonance[ring], 5.0)  # Cap it
        
        # logger.debug(f"Spring ring {ring}: resonance += {delta * 0.5}")
    
    def on_encoder_press(self, ring: int):
        """Center all particles on ring."""
        for particle in self.physics.rings[ring]:
            particle.position = self.centers[ring]
            particle.velocity = 0
        self.resonance[ring] = 0
        logger.info(f"Spring ring {ring} centered")
    
    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        """Display resonating particles."""
        result = []
        
        # Background: show center point
        result.append((int(self.centers[ring]) % 64, 3))
        
        # Particles
        for particle in self.physics.rings[ring]:
            pos = int(particle.position) % 64
            brightness = int(particle.brightness + self.resonance[ring] * 2)
            brightness = min(15, brightness)
            
            if brightness > 0:
                result.append((pos, brightness))
        
        return result
    
    def teletype_command(self, command: str):
        """
        Teletype control:
        - SPRING.K <ring> <stiffness> - Set spring constant
        - SPRING.CENTER <ring> <pos> - Set center point
        - SPRING.RESET - Reset all
        """
        parts = command.split()
        
        if len(parts) == 0:
            return
        
        cmd = parts[0].upper()
        
        if cmd == "K" and len(parts) == 3:
            ring = int(parts[1])
            k = float(parts[2])
            if 0 <= ring < 4:
                self.spring_constant[ring] = max(0.1, min(5.0, k))
                logger.info(f"Spring ring {ring}: k = {k}")
        
        elif cmd == "CENTER" and len(parts) == 3:
            ring = int(parts[1])
            center = int(parts[2])
            if 0 <= ring < 4 and 0 <= center < 64:
                self.centers[ring] = center
                logger.info(f"Spring ring {ring}: center = {center}")
        
        elif cmd == "RESET":
            for ring_idx in range(4):
                self.resonance[ring_idx] = 0
                for particle in self.physics.rings[ring_idx]:
                    particle.position = self.centers[ring_idx]
                    particle.velocity = 0
            logger.info("Spring reset")
