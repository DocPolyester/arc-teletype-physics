"""
Physics Engine für Arc-basierte Anwendungen
Unterstützt verschiedene Kraft-Modelle und Physik-Simulationen
"""
import math
import logging
from typing import List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PhysicsMode(Enum):
    """Verfügbare Physics Modi."""
    CYCLES = "cycles"           # Classic Cycles (keine Physics)
    PENDULUM = "pendulum"       # Pendel mit Schwerkraft
    GRAVITY = "gravity"         # Gravitation/Particle System
    SPRING = "spring"           # Federmechanik (Resonator)
    ORBIT = "orbit"             # Orbitalphysik (Zentripetal)


@dataclass
class Particle:
    """Ein Partikel in der Physik-Simulation."""
    position: float        # 0-63 (Position auf dem Arc Ring)
    velocity: float        # Position change per frame
    mass: float = 1.0      # Masse für Kraft-Berechnungen
    brightness: int = 8    # LED Helligkeit
    
    def update(self, force: float, dt: float = 0.016):
        """Update position based on force (Newton)."""
        acceleration = force / self.mass
        self.velocity += acceleration * dt
        self.position += self.velocity * dt
        
        # Damping (Energieverlust)
        self.velocity *= 0.98
    
    def wrap_position(self):
        """Wrap position to 0-63 range."""
        while self.position < 0:
            self.position += 64
        while self.position >= 64:
            self.position -= 64


class PhysicsEngine:
    """
    Basis Physics Engine für Arc Particle Systems.
    Unterstützt verschiedene Kraft-Modelle.
    """
    
    def __init__(self, num_rings: int = 4):
        """
        Initialize Physics Engine.
        
        Args:
            num_rings: Number of Arc rings (usually 4)
        """
        self.num_rings = num_rings
        self.rings = [[Particle(i * 16, 0) for i in range(4)] for _ in range(num_rings)]
        self.dt = 0.016  # 60 FPS
        self.gravity = -2.0  # Gravitational acceleration
        self.damping = 0.98
    
    def apply_gravity(self, strength: float = 1.0):
        """Apply gravitational force downward."""
        for ring_particles in self.rings:
            for particle in ring_particles:
                # Gravity - Richtung zum "Boden" (Position 32 = unten)
                delta = 32 - particle.position
                force = self.gravity * strength * (delta / 32.0)
                particle.update(force, self.dt)
    
    def apply_spring_force(self, center: float, strength: float = 0.5):
        """Apply spring/resonator force toward center point."""
        for ring_particles in self.rings:
            for particle in ring_particles:
                # Hooke's Law: F = -k * x
                delta = center - particle.position
                
                # Shortest path on circle
                if delta > 32:
                    delta -= 64
                elif delta < -32:
                    delta += 64
                
                force = strength * delta
                particle.update(force, self.dt)
    
    def apply_pendulum_force(self, angle: float, strength: float = 1.5):
        """
        Apply pendulum force - oscillates like a swinging pendulum.
        Combines gravity and angular momentum.
        """
        for ring_particles in self.rings:
            for particle in ring_particles:
                # Pendulum equation: F = -g/L * sin(theta)
                # We simulate this as force toward equilibrium
                equilibrium = 32 + 16 * math.sin(angle)
                delta = equilibrium - particle.position
                
                # Wrap around
                if delta > 32:
                    delta -= 64
                elif delta < -32:
                    delta += 64
                
                force = strength * delta / 10.0
                particle.update(force, self.dt)
    
    def apply_central_force(self, center: float, strength: float = 1.0, mode: str = "attract"):
        """
        Apply central force (orbital mechanics).
        
        Args:
            center: Center position
            strength: Force strength
            mode: "attract" (gravity), "repel" (explosion), "orbit" (stable)
        """
        for ring_particles in self.rings:
            for particle in ring_particles:
                delta = center - particle.position
                
                # Wrap to shortest path
                if delta > 32:
                    delta -= 64
                elif delta < -32:
                    delta += 64
                
                distance = abs(delta)
                
                if distance < 0.1:
                    distance = 0.1
                
                # F = strength / distance^2 (Newton's law)
                force_magnitude = strength / (distance * distance + 1)
                
                if mode == "attract":
                    force = force_magnitude if delta > 0 else -force_magnitude
                elif mode == "repel":
                    force = -force_magnitude if delta > 0 else force_magnitude
                elif mode == "orbit":
                    # Tangential force for stable orbit
                    force = force_magnitude * math.sin(particle.position / 32 * math.pi)
                
                particle.update(force, self.dt)
    
    def apply_wave(self, wave_center: float, wave_strength: float = 0.8, wavelength: float = 16):
        """Apply wave/ripple effect spreading from center."""
        for ring_particles in self.rings:
            for particle in ring_particles:
                delta = particle.position - wave_center
                
                # Wrap
                if delta > 32:
                    delta -= 64
                elif delta < -32:
                    delta += 64
                
                # Wave equation: sin(kx - ωt)
                wave = math.sin(delta / wavelength * math.pi) * wave_strength
                particle.update(wave, self.dt)
    
    def get_ring_display(self, ring_idx: int) -> List[Tuple[int, int]]:
        """
        Get display data for a ring.
        
        Returns:
            List of (position, brightness) tuples
        """
        if ring_idx >= self.num_rings:
            return []
        
        result = []
        for i in range(64):
            brightness = 0
            
            # Iterate through particles and accumulate brightness
            for particle in self.rings[ring_idx]:
                particle.wrap_position()
                dist = abs(particle.position - i)
                
                # Wrap around circle
                if dist > 32:
                    dist = 64 - dist
                
                # Gaussian falloff for LED brightness
                brightness_contrib = particle.brightness * math.exp(-(dist**2) / 8)
                brightness = min(15, int(brightness + brightness_contrib))
            
            result.append((i, brightness))
        
        return result
    
    def update_all(self):
        """Update all particles."""
        for ring_particles in self.rings:
            for particle in ring_particles:
                particle.wrap_position()
    
    def reset(self):
        """Reset all particles."""
        for ring_particles in self.rings:
            for particle in ring_particles:
                particle.position = 0
                particle.velocity = 0
