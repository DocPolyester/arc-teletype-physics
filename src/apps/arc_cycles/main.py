"""
Arc Cycles Application - Main controller with mode management
"""
import logging
import subprocess
import time
from typing import Dict, Optional

from hardware.arc import ArcController
from hardware.arduino_serial import ArduinoSerialHandler

from .modes.cycles_mode import CyclesMode
from .modes.pendulum_mode import PendulumMode
from .modes.gravity_mode import GravityMode
from .modes.spring_mode import SpringMode
from .modes.orbit_mode import OrbitMode
from .modes.swing_mode import SwingMode

logger = logging.getLogger(__name__)


class ArcCyclesApp:
    """
    Arc Cycles Application - Multi-mode physics-based Arc controller.
    Supports: Cycles, Pendulum, Gravity, Spring, Orbit, Swing modes.
    """
    
    def __init__(self, arc: ArcController,
                 i2c_slave: Optional[ArduinoSerialHandler] = None, num_rings: int = 4):
        """
        Initialize Arc Cycles App.

        Args:
            arc: ArcController instance
            i2c_slave: Optional ArduinoSerialHandler (Arduino Nano als Teletype I2C Slave)
        """
        self.arc = arc
        self.i2c_slave = i2c_slave
        self.num_rings = num_rings

        # Initialize modes
        self.modes: Dict[str, any] = {
            "cycles": CyclesMode(arc, num_rings=num_rings),
            "pendulum": PendulumMode(arc),
            "gravity": GravityMode(arc),
            "spring": SpringMode(arc),
            "orbit": OrbitMode(arc),
            "swing": SwingMode(arc),
        }
        
        # Current mode
        self.current_mode_name = "cycles"
        self.current_mode = self.modes["cycles"]
        self.current_mode.activate()
        
        # Running state
        self.running = False
        self.frame_count = 0
        self.last_update = time.time()
        self._press_times: Dict[int, float] = {}   # ring → letzter Press-Zeitstempel

        # Connect I2C slave handler
        if self.i2c_slave:
            self.i2c_slave.set_app(self)
            self.i2c_slave.start()

        logger.info("Arc Cycles App initialized")
    
    def set_mode(self, mode_name: str):
        """
        Switch to a different mode.
        
        Args:
            mode_name: Name of mode ("cycles", "pendulum", etc.)
        """
        if mode_name not in self.modes:
            logger.warning(f"Unknown mode: {mode_name}")
            return
        
        if mode_name == self.current_mode_name:
            return  # Already on this mode
        
        # Deactivate current mode
        self.current_mode.deactivate()
        
        # Activate new mode
        self.current_mode_name = mode_name
        self.current_mode = self.modes[mode_name]
        self.current_mode.activate()
        
        logger.info(f"Switched to mode: {mode_name}")

    def set_arc_orientation(self, offset: int):
        """ARC-Ausrichtung setzen. offset in LEDs (0=quer, 48=hochkant/270°)."""
        for mode in self.modes.values():
            mode.arc_offset = offset
        logger.info(f"ARC Orientierung: offset={offset} LEDs")
    
    def update(self):
        """
        Main update loop.
        Should be called frequently (60 FPS ideal).
        """
        # Calculate delta time
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        
        # Cap dt to prevent big jumps
        dt = min(dt, 0.05)
        
        # Update current mode
        self.current_mode.update(dt)

        # Sync physics state to I2C slave EEPROM (Teletype reads from here)
        if self.i2c_slave:
            self.i2c_slave.update_state(self)

        # Display on Arc
        self.current_mode.display()

        self.frame_count += 1
    
    def on_encoder_turn(self, ring: int, delta: int):
        """
        Handle Arc encoder rotation.
        
        Args:
            ring: Ring index (0-3)
            delta: Rotation delta
        """
        self.current_mode.on_encoder_turn(ring, delta)
    
    def on_encoder_press(self, ring: int):
        """Handle Arc encoder press."""
        now = time.time()
        self._press_times[ring] = now

        # Shutdown: Encoder 1 + 2 (ring 0 + 1) innerhalb von 2 Sekunden
        t0 = self._press_times.get(0, 0.0)
        t1 = self._press_times.get(1, 0.0)
        if t0 > 0 and t1 > 0 and abs(t0 - t1) < 2.0:
            logger.info("Encoder 0+1 gleichzeitig gedrückt → RPi Shutdown")
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
            return

        self.current_mode.on_encoder_press(ring)
    
    def on_teletype_command(self, command: str):
        """
        Handle Teletype commands.
        Format: <MODE>.<COMMAND> [args...]
        
        Examples:
        - CYCLES.RESET
        - PEND.PERIOD 0 1000
        - GRAV.STRENGTH 5
        - MODE.GRAVITY (switch mode)
        """
        parts = command.strip().upper().split()
        
        if not parts:
            return
        
        if parts[0].startswith("MODE."):
            # Mode switching: MODE.CYCLES, MODE.PENDULUM, etc.
            mode_name = parts[0][5:].lower()
            self.set_mode(mode_name)
            return
        
        # Route to current mode if it starts with mode prefix
        if "." in parts[0]:
            mode_prefix = parts[0].split(".")[0].lower()
            
            # Find matching mode
            for mode_name, mode in self.modes.items():
                if mode_name.upper() == mode_prefix or \
                   mode_name[:4].upper() == mode_prefix[:4]:
                    mode.teletype_command(" ".join(parts[0].split(".")[1:] + parts[1:]))
                    return
    
    def start(self):
        """Start the app main loop."""
        self.running = True
        logger.info("Arc Cycles App started")
        
        try:
            while self.running:
                self.update()
                time.sleep(0.016)  # ~60 FPS
        
        except KeyboardInterrupt:
            logger.info("Interrupted")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the app."""
        self.running = False
        if self.i2c_slave:
            self.i2c_slave.stop()
        self.current_mode.clear_display()
        logger.info("Arc Cycles App stopped")
    
    def get_status(self) -> Dict:
        """Get app status for monitoring."""
        return {
            "current_mode": self.current_mode_name,
            "frame_count": self.frame_count,
            "available_modes": list(self.modes.keys()),
        }
