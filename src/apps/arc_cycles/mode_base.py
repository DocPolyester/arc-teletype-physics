"""
Mode Base Class - Abstract base for all Arc modes
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from hardware.arc import ArcController
import logging

logger = logging.getLogger(__name__)


class ArcMode(ABC):
    """Base class for Arc interaction modes."""
    
    def __init__(self, arc: ArcController, name: str):
        """
        Initialize Arc Mode.
        
        Args:
            arc: ArcController instance
            name: Mode name
        """
        self.arc = arc
        self.name = name
        self.is_active = False
        self.arc_offset = 0   # LED-Rotation: 0=quer (default), 48=hochkant (270°)
        self._level_bufs = [bytearray(64) for _ in range(4)]
        logger.info(f"Mode '{name}' initialized")
    
    @abstractmethod
    def update(self, dt: float = 0.016):
        """
        Update mode state.
        Should be called every frame.
        
        Args:
            dt: Delta time in seconds
        """
        pass
    
    @abstractmethod
    def on_encoder_turn(self, ring: int, delta: int):
        """
        Handle encoder turn.
        
        Args:
            ring: Ring index (0-3)
            delta: Rotation direction/magnitude
        """
        pass
    
    @abstractmethod
    def on_encoder_press(self, ring: int):
        """Handle encoder press."""
        pass
    
    def display(self):
        """Send display data to Arc — full ring map per frame, no ghost LEDs."""
        num_rings = getattr(self, "num_rings", 4)
        offset = self.arc_offset
        for ring in range(num_rings):
            buf = self._level_bufs[ring]
            buf[:] = b"\x00" * 64
            for pos, brightness in self.get_ring_display(ring):
                buf[(pos + offset) % 64] = max(0, min(15, brightness))
            self.arc.set_ring_map(ring, buf)

    def display_for_ring(self, physical_ring: int):
        """Render this mode's internal ring 0 to a specific physical ring."""
        buf = self._level_bufs[0]
        buf[:] = b"\x00" * 64
        offset = self.arc_offset
        for pos, brightness in self.get_ring_display(0):
            buf[(pos + offset) % 64] = max(0, min(15, brightness))
        self.arc.set_ring_map(physical_ring, buf)

    def clear_display(self):
        num_rings = getattr(self, "num_rings", 4)
        for ring in range(num_rings):
            self.arc.clear_ring(ring)
    
    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        """
        Get display data for ring.
        
        Returns:
            List of (position, brightness) tuples
        """
        return []
    
    def activate(self):
        """Called when mode is activated."""
        self.is_active = True
        logger.info(f"Mode '{self.name}' activated")
    
    def deactivate(self):
        """Called when mode is deactivated."""
        self.is_active = False
        self.clear_display()
        logger.info(f"Mode '{self.name}' deactivated")
    
    def teletype_command(self, command: str):
        """
        Process Teletype command.
        Allows Teletype to control this mode.
        """
        pass


class MultiRingMode:
    """
    Base class for modes that own multiple physical rings simultaneously.
    Unlike ArcMode (which always operates on internal ring 0), a MultiRingMode
    directly controls a list of physical rings and handles their display itself.
    """

    def __init__(self, rings: list, arc: "ArcController", arc_offset: int = 0):
        self.rings      = rings       # physical ring indices this group owns
        self.arc        = arc
        self.arc_offset = arc_offset

    def update(self, dt: float):
        pass

    def display(self):
        pass

    def on_encoder_turn(self, ring: int, delta: int):
        pass

    def on_encoder_press(self, ring: int):
        pass

    def get_iiq_value(self, ring: int, vtype: int) -> int:
        """
        Return IIQ readout for a physical ring owned by this group.
        vtype: 0=position, 1=velocity, 2=angle, 3=param1
        Override in subclasses to expose meaningful values to Teletype.
        """
        return 0

    def _send_ring(self, physical_ring: int, leds: list):
        """Send a 64-element brightness list to a physical ring, applying orientation."""
        buf = bytearray(64)
        off = self.arc_offset
        for i, b in enumerate(leds):
            buf[(i + off) % 64] = max(0, min(15, b))
        self.arc.set_ring_map(physical_ring, buf)
