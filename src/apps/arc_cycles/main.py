"""
Arc Cycles Application - Main controller with per-ring mode management
"""
import logging
import queue
import subprocess
import time
from typing import Dict, List, Optional

from hardware.arc import ArcController
from hardware.arduino_serial import ArduinoSerialHandler

from .mode_base import ArcMode, MultiRingMode
from .modes.cycles_mode import CyclesMode
from .modes.pendulum_mode import PendulumMode
from .modes.gravity_mode import GravityMode
from .modes.spring_mode import SpringMode
from .modes.orbit_mode import OrbitMode
from .modes.swing_mode import SwingMode
from .modes.euclidean_mode import EuclideanMode
from .modes.bounce_mode import BounceMode
from .modes.drunk_mode import DrunkMode
from .modes.chaos_mode import ChaosMode
from .modes.probability_mode import ProbabilityMode
from .modes.phase_shift_mode import PhaseShiftMode
from .modes.turing_machine_mode import TuringMachine2x2

logger = logging.getLogger(__name__)

MULTI_RING_CLASSES = {
    "phase_shift":    PhaseShiftMode,
    "turing_2x2":    TuringMachine2x2,
}

MODE_CLASSES = {
    "cycles":      CyclesMode,
    "pendulum":    PendulumMode,
    "gravity":     GravityMode,
    "spring":      SpringMode,
    "orbit":       OrbitMode,
    "swing":       SwingMode,
    "euclidean":   EuclideanMode,
    "bounce":      BounceMode,
    "drunk":       DrunkMode,
    "chaos":       ChaosMode,
    "probability": ProbabilityMode,
}


class ArcCyclesApp:
    """
    Arc Cycles — each of the 4 rings can run a different physics mode independently.
    Encoder events route to the matching per-ring instance (internal ring index 0).
    """

    def __init__(self, arc: ArcController,
                 i2c_slave: Optional[ArduinoSerialHandler] = None,
                 num_rings: int = 4,
                 default_mode: str = "cycles",
                 ring_modes: Optional[List[str]] = None):
        self.arc       = arc
        self.i2c_slave = i2c_slave
        self.num_rings = num_rings

        if ring_modes is None:
            ring_modes = [default_mode] * num_rings

        self.ring_instances: List[ArcMode]  = []
        self.ring_mode_names: List[str]     = []
        for r in range(num_rings):
            name = ring_modes[r] if r < len(ring_modes) else default_mode
            inst = self._make_instance(name, r)
            inst.activate()
            self.ring_instances.append(inst)
            self.ring_mode_names.append(name)

        # Multi-ring parallel layer
        self.ring_claimed_by: List[str]         = ['single'] * num_rings
        self.multi_ring_groups: List[MultiRingMode] = []

        self.running     = False
        self.frame_count = 0
        self.last_update = time.time()
        self._encoder_queue: queue.Queue = queue.Queue()
        self._shutdown_press_time: float = 0.0

        if self.i2c_slave:
            self.i2c_slave.set_app(self)
            self.i2c_slave.start()

        logger.info(f"Arc Cycles App initialized — ring modes: {self.ring_mode_names}")

    # ------------------------------------------------------------------ #
    #  Instance factory                                                    #
    # ------------------------------------------------------------------ #

    def _make_instance(self, mode_name: str, ring_index: int = 0) -> ArcMode:
        name = mode_name if mode_name in MODE_CLASSES else "cycles"
        cls  = MODE_CLASSES[name]
        if name == "cycles":
            return cls(self.arc, num_rings=1)
        return cls(self.arc, num_rings=1, ring_hint=ring_index)

    # ------------------------------------------------------------------ #
    #  Mode switching                                                      #
    # ------------------------------------------------------------------ #

    def set_mode(self, mode_name: str):
        """Set all rings to the same single-ring mode (releases any multi-ring groups)."""
        if mode_name not in MODE_CLASSES:
            logger.warning(f"Unknown mode: {mode_name}")
            return
        self._deactivate_multi()
        for r in range(self.num_rings):
            self._replace_ring(r, mode_name)
        logger.info(f"All rings → {mode_name}")

    def set_ring_mode(self, ring: int, mode_name: str):
        """Set a single ring to a different single-ring mode."""
        if mode_name not in MODE_CLASSES or not (0 <= ring < self.num_rings):
            logger.warning(f"set_ring_mode: invalid ring={ring} or mode={mode_name}")
            return
        # Release ring from any multi-ring group that owns it
        self._release_ring_from_multi(ring)
        self._replace_ring(ring, mode_name)
        logger.info(f"Ring {ring} → {mode_name}")

    def activate_multi_mode(self, mode_name: str, groups: list):
        """
        Activate a multi-ring mode.
        groups: list of ring-index lists, one per group instance.
        Example: activate_multi_mode("phase_shift", [[0,1],[2,3]])
        """
        if mode_name not in MULTI_RING_CLASSES:
            logger.warning(f"Unknown multi-ring mode: {mode_name}")
            return
        cls = MULTI_RING_CLASSES[mode_name]
        self._deactivate_multi()
        offset = self.ring_instances[0].arc_offset
        for rings in groups:
            for r in rings:
                self.arc.clear_ring(r)
                self.ring_claimed_by[r] = 'multi'
            group = cls(rings=rings, arc=self.arc, arc_offset=offset)
            self.multi_ring_groups.append(group)
        logger.info(f"Multi-ring mode '{mode_name}' active on groups {groups}")

    def _deactivate_multi(self):
        for group in self.multi_ring_groups:
            for r in group.rings:
                self.arc.clear_ring(r)
                self.ring_claimed_by[r] = 'single'
        self.multi_ring_groups.clear()

    def _release_ring_from_multi(self, ring: int):
        if self.ring_claimed_by[ring] != 'multi':
            return
        self.multi_ring_groups = [g for g in self.multi_ring_groups if ring not in g.rings]
        self.ring_claimed_by[ring] = 'single'

    def _replace_ring(self, ring: int, mode_name: str):
        self.arc.clear_ring(ring)
        old_offset = self.ring_instances[ring].arc_offset
        inst = self._make_instance(mode_name, ring)
        inst.arc_offset = old_offset
        inst.activate()
        self.ring_instances[ring]  = inst
        self.ring_mode_names[ring] = mode_name

    # ------------------------------------------------------------------ #
    #  Orientation                                                         #
    # ------------------------------------------------------------------ #

    def set_arc_orientation(self, offset: int):
        for inst in self.ring_instances:
            inst.arc_offset = offset
        for group in self.multi_ring_groups:
            group.arc_offset = offset
        logger.info(f"ARC orientation: offset={offset} LEDs")

    # ------------------------------------------------------------------ #
    #  Main loop                                                           #
    # ------------------------------------------------------------------ #

    def update(self):
        now = time.time()
        dt  = min(now - self.last_update, 0.05)
        self.last_update = now

        # Drain encoder queue
        while True:
            try:
                ring, delta = self._encoder_queue.get_nowait()
                if 0 <= ring < self.num_rings:
                    if self.ring_claimed_by[ring] == 'multi':
                        for g in self.multi_ring_groups:
                            if ring in g.rings:
                                g.on_encoder_turn(ring, delta)
                    else:
                        self.ring_instances[ring].on_encoder_turn(0, delta)
            except queue.Empty:
                break

        # Single-ring physics update
        for r in range(self.num_rings):
            if self.ring_claimed_by[r] == 'single':
                self.ring_instances[r].update(dt)

        # Multi-ring physics update
        for group in self.multi_ring_groups:
            group.update(dt)

        # Sync state to I2C bridge (Teletype reads from here)
        if self.i2c_slave:
            self.i2c_slave.update_state(self)

        # Display: single-ring
        for r in range(self.num_rings):
            if self.ring_claimed_by[r] == 'single':
                self.ring_instances[r].display_for_ring(r)

        # Display: multi-ring
        for group in self.multi_ring_groups:
            group.display()

        self.frame_count += 1

    # ------------------------------------------------------------------ #
    #  Encoder callbacks (called from OSC thread)                         #
    # ------------------------------------------------------------------ #

    def on_encoder_turn(self, ring: int, delta: int):
        self._encoder_queue.put((ring, delta))

    def on_encoder_press(self, ring: int):
        if ring == 0:
            self._shutdown_press_time = time.time()
        elif 0 <= ring < self.num_rings:
            if self.ring_claimed_by[ring] == 'multi':
                for g in self.multi_ring_groups:
                    if ring in g.rings:
                        g.on_encoder_press(ring)
            else:
                self.ring_instances[ring].on_encoder_press(0)

    def on_encoder_release(self, ring: int):
        if ring == 0:
            held = time.time() - self._shutdown_press_time
            self._shutdown_press_time = 0.0
            if held > 2.0:
                logger.info("Long press encoder 0 → RPi Shutdown")
                subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
            else:
                if self.ring_claimed_by[0] == 'multi':
                    for g in self.multi_ring_groups:
                        if 0 in g.rings:
                            g.on_encoder_press(0)
                else:
                    self.ring_instances[0].on_encoder_press(0)

    # ------------------------------------------------------------------ #
    #  Teletype text commands (routed from arduino_serial via on_teletype) #
    # ------------------------------------------------------------------ #

    def on_teletype_command(self, command: str):
        """Route MODE.xxx or PREFIX.cmd to matching ring instances."""
        parts = command.strip().upper().split()
        if not parts:
            return
        if parts[0].startswith("MODE."):
            self.set_mode(parts[0][5:].lower())
            return
        if "." in parts[0]:
            mode_prefix = parts[0].split(".")[0].lower()
            cmd_suffix  = " ".join(parts[0].split(".")[1:] + parts[1:])
            for name, inst in zip(self.ring_mode_names, self.ring_instances):
                if name.startswith(mode_prefix[:4]):
                    inst.teletype_command(cmd_suffix)

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def start(self):
        self.running = True
        logger.info("Arc Cycles App started")
        _target = 1.0 / 60.0
        try:
            while self.running:
                t0 = time.perf_counter()
                try:
                    self.update()
                except Exception as e:
                    logger.error(f"Frame error: {e}", exc_info=True)
                remaining = _target - (time.perf_counter() - t0)
                if remaining > 0.001:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            logger.info("Interrupted")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.i2c_slave:
            self.i2c_slave.stop()
        for r in range(self.num_rings):
            self.arc.clear_ring(r)
        logger.info("Arc Cycles App stopped")

    def get_status(self) -> Dict:
        return {
            "ring_modes":       list(self.ring_mode_names),
            "frame_count":      self.frame_count,
            "available_modes":  list(MODE_CLASSES.keys()),
        }

    # ------------------------------------------------------------------ #
    #  Backward-compat properties (used by arduino_serial for logging)    #
    # ------------------------------------------------------------------ #

    @property
    def current_mode_name(self) -> str:
        return self.ring_mode_names[0] if self.ring_mode_names else "cycles"

    @property
    def current_mode(self) -> Optional[ArcMode]:
        return self.ring_instances[0] if self.ring_instances else None
