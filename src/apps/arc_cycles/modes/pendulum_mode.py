"""
Pendulum Mode - Physics simulation with gravity and oscillation
"""
import math
import logging
from typing import List, Tuple
from ..physics import PhysicsEngine, Particle
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)


class PendulumMode(ArcMode):
    """
    Pendulum Mode - Four pendulums oscillating under gravity.
    Each ring is an independent pendulum with different periods.
    """
    
    def __init__(self, arc):
        super().__init__(arc, "Pendulum")
        
        self.physics = PhysicsEngine(num_rings=4)
        self.time = 0.0
        
        # Pendulum parameters per ring
        # Longer pendulum = slower oscillation
        self.periods = [1.0, 1.5, 2.0, 2.5]  # seconds
        self.amplitudes = [16, 16, 16, 16]   # Position amplitude
        self.centers = [32, 32, 32, 32]      # Equilibrium position
        
        # Input modulation
        self.encoder_force = [0, 0, 0, 0]
    
    def update(self, dt: float = 0.016):
        """Update physics simulation."""
        self.time += dt
        
        # Apply pendulum physics to each ring
        for ring_idx in range(4):
            # Angular position: simple harmonic motion
            omega = 2 * math.pi / self.periods[ring_idx]
            angle = omega * self.time
            
            # Position from pendulum
            phase_offset = ring_idx * math.pi / 2  # Stagger phases
            equilibrium = self.centers[ring_idx] + self.amplitudes[ring_idx] * math.sin(angle + phase_offset)
            
            # Get the particle for this ring
            particle = self.physics.rings[ring_idx][0]
            particle.position = equilibrium
            
            # Add encoder-based perturbation
            if self.encoder_force[ring_idx] != 0:
                particle.velocity += self.encoder_force[ring_idx]
                self.encoder_force[ring_idx] *= 0.9
    
    def on_encoder_turn(self, ring: int, delta: int):
        """Encoder turn adds energy to pendulum."""
        self.encoder_force[ring] = delta * 2
        # logger.debug(f"Pendulum ring {ring}: impulse {delta}")
    
    def on_encoder_press(self, ring: int):
        """Reset pendulum to center."""
        self.physics.rings[ring][0].position = self.centers[ring]
        self.physics.rings[ring][0].velocity = 0
        logger.info(f"Pendulum ring {ring} reset")
    
    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        """Display pendulum as bright spot with trail."""
        result = []
        particle = self.physics.rings[ring][0]
        pos = int(particle.position) % 64
        
        # Main LED
        brightness = 14
        result.append((pos, brightness))
        
        # Small trail effect
        for trail in range(1, 4):
            trail_pos = (pos - trail) % 64
            trail_brightness = max(0, 6 - trail * 2)
            if trail_brightness > 0:
                result.append((trail_pos, trail_brightness))
        
        return result
    
    def teletype_command(self, command: str):
        """
        Teletype control:
        - PEND.PERIOD <ring> <period_ms> - Set oscillation period
        - PEND.AMP <ring> <amplitude> - Set swing amplitude
        - PEND.RESET - Reset all
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
                logger.info(f"Ring {ring} period: {period_ms}ms")
        
        elif cmd == "AMP" and len(parts) == 3:
            ring = int(parts[1])
            amp = int(parts[2])
            if 0 <= ring < 4 and 0 <= amp <= 32:
                self.amplitudes[ring] = amp
                logger.info(f"Ring {ring} amplitude: {amp}")
        
        elif cmd == "RESET":
            self.time = 0
            logger.info("Pendulum reset")
