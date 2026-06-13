"""
Orbit Mode - Orbital mechanics simulation
"""
import logging
import math
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)


class OrbitMode(ArcMode):
    """
    Orbit Mode - Particles orbit around a central point.
    Multiple particles create complex orbital patterns.
    Similar to planetary systems or atomic models.
    """
    
    def __init__(self, arc):
        super().__init__(arc, "Orbit")
        
        # Orbital parameters per ring
        self.time = 0.0
        self.radii = [12, 16, 20, 24]        # Orbit radius
        self.periods = [1.0, 1.5, 2.0, 1.2]  # Orbital periods (seconds)
        self.particle_counts = [3, 3, 4, 4]  # Particles per ring
        self.centers = [32, 32, 32, 32]      # Center positions
        
        # Encoder interaction
        self.angular_velocities = [0, 0, 0, 0]
        self.ang_accel = [0, 0, 0, 0]
    
    def update(self, dt: float = 0.016):
        """Update orbital positions."""
        self.time += dt
        
        # Update angular velocities (with friction)
        for ring_idx in range(4):
            self.angular_velocities[ring_idx] += self.ang_accel[ring_idx]
            self.angular_velocities[ring_idx] *= 0.98
            self.ang_accel[ring_idx] *= 0.95
    
    def on_encoder_turn(self, ring: int, delta: int):
        """Encoder turn changes angular velocity (like gravity assist)."""
        self.ang_accel[ring] += delta * 0.3
        # logger.debug(f"Orbit ring {ring}: angular accel += {delta * 0.3}")
    
    def on_encoder_press(self, ring: int):
        """Reset orbit on press."""
        self.angular_velocities[ring] = 0
        self.ang_accel[ring] = 0
        logger.info(f"Orbit ring {ring} reset")
    
    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        """Display orbiting particles."""
        result = []
        
        # Center point (dim)
        result.append((int(self.centers[ring]) % 64, 2))
        
        # Particles
        num_particles = self.particle_counts[ring]
        period = self.periods[ring]
        radius = self.radii[ring]
        
        for particle_idx in range(num_particles):
            # Angular position
            phase_offset = particle_idx * 2 * math.pi / num_particles
            angular_vel = 2 * math.pi / period
            angular_vel += self.angular_velocities[ring]
            
            angle = angular_vel * self.time + phase_offset
            
            # Convert to ring position (0-63)
            # Radius affects position offset from center
            pos_offset = radius * math.sin(angle)
            pos = (self.centers[ring] + pos_offset) % 64
            
            # Brightness varies with orbit for 3D effect
            brightness = int(8 + 4 * math.cos(angle))
            brightness = max(1, min(15, brightness))
            
            result.append((int(pos), brightness))
        
        return result
    
    def teletype_command(self, command: str):
        """
        Teletype control:
        - ORBIT.PERIOD <ring> <period_ms> - Set orbital period
        - ORBIT.RADIUS <ring> <radius> - Set orbit radius
        - ORBIT.PARTICLES <ring> <count> - Number of orbiting bodies
        """
        parts = command.split()
        
        if len(parts) == 0:
            return
        
        cmd = parts[0].upper()
        
        if cmd == "PERIOD" and len(parts) == 3:
            ring = int(parts[1])
            period_ms = int(parts[2])
            if 0 <= ring < 4:
                self.periods[ring] = period_ms / 1000.0
                logger.info(f"Orbit ring {ring}: period = {period_ms}ms")
        
        elif cmd == "RADIUS" and len(parts) == 3:
            ring = int(parts[1])
            radius = int(parts[2])
            if 0 <= ring < 4 and 0 <= radius <= 32:
                self.radii[ring] = radius
                logger.info(f"Orbit ring {ring}: radius = {radius}")
        
        elif cmd == "PARTICLES" and len(parts) == 3:
            ring = int(parts[1])
            count = int(parts[2])
            if 0 <= ring < 4 and 1 <= count <= 8:
                self.particle_counts[ring] = count
                logger.info(f"Orbit ring {ring}: {count} particles")
