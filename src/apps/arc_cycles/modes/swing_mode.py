"""
Swing Mode - Real pendulum physics with nonlinear ODE
"""
import math
import logging
from typing import List, Tuple
from ..mode_base import ArcMode

logger = logging.getLogger(__name__)


class SwingMode(ArcMode):
    """
    Four independent pendulums with nonlinear physics.
    Different lengths give different natural periods (~1 / 2 / 3 / 4 s).
    Encoder turn adds angular impulse; press resets to rest.
    """

    GRAVITY = 9.8                        # m/s²
    CENTER  = 32                         # equilibrium LED position (0-63)
    SCALE   = 20.0 / (math.pi / 2)      # LEDs per radian — π/2 maps to ±20 LEDs
    LENGTHS = [0.25, 1.0, 2.25, 4.0]    # pendulum lengths in m
    IMPULSE = 0.8                        # rad/s added per encoder tick

    def __init__(self, arc):
        super().__init__(arc, "Swing")
        self.num_rings = 4
        self.damping = 0.4               # angular damping coefficient (rad/s per rad/s)

        # Start each pendulum displaced so the motion is immediately visible
        self.theta = [math.pi/4, math.pi/3, -math.pi/5, -math.pi/6]
        self.omega = [0.0, 0.0, 0.0, 0.0]

    def _omega_n(self, ring: int) -> float:
        """Natural angular frequency sqrt(g/L)."""
        return math.sqrt(self.GRAVITY / self.LENGTHS[ring])

    def _derivatives(self, ring: int, theta: float, omega: float):
        on = self._omega_n(ring)
        # Nonlinear pendulum ODE: θ'' = -(g/L)·sin(θ) - b·θ'
        return omega, -(on * on) * math.sin(theta) - self.damping * omega

    def update(self, dt: float = 0.016):
        for i in range(self.num_rings):
            t, o = self.theta[i], self.omega[i]
            # RK4 integration
            k1t, k1o = self._derivatives(i, t, o)
            k2t, k2o = self._derivatives(i, t + k1t*dt/2, o + k1o*dt/2)
            k3t, k3o = self._derivatives(i, t + k2t*dt/2, o + k2o*dt/2)
            k4t, k4o = self._derivatives(i, t + k3t*dt,   o + k3o*dt)
            self.theta[i] = t + (k1t + 2*k2t + 2*k3t + k4t) * dt / 6
            self.omega[i] = o + (k1o + 2*k2o + 2*k3o + k4o) * dt / 6

    def on_encoder_turn(self, ring: int, delta: int):
        if 0 <= ring < self.num_rings:
            self.omega[ring] += delta * self.IMPULSE
            logger.debug(f"Swing ring {ring}: omega={self.omega[ring]:.2f}")

    def on_encoder_press(self, ring: int):
        if 0 <= ring < self.num_rings:
            self.theta[ring] = 0.0
            self.omega[ring] = 0.0
            logger.info(f"Swing ring {ring} reset to rest")

    def get_ring_display(self, ring: int) -> List[Tuple[int, int]]:
        theta = self.theta[ring]
        omega = self.omega[ring]
        pos = int(round(self.CENTER + theta * self.SCALE)) % 64

        # Bright at equilibrium (max speed), dim at the turning points
        speed_norm = min(1.0, abs(omega) / max(0.01, self._omega_n(ring) * 2))
        brightness = max(6, int(6 + speed_norm * 9))

        result = [(pos, brightness)]

        # Trail behind the direction of travel
        trail_dir = -1 if omega >= 0 else 1
        for step in range(1, 6):
            tb = brightness - step * 3
            if tb <= 0:
                break
            result.append(((pos + trail_dir * step) % 64, tb))

        # Dim equilibrium marker so the user can see where rest is
        result.append((self.CENTER, 1))

        return result

    def teletype_command(self, command: str):
        """
        SWING.RESET            — stop all pendulums
        SWING.KICK <ring> <v>  — add angular velocity impulse (rad/s)
        SWING.DAMP <b>         — set damping coefficient (default 0.4)
        """
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].upper()

        if cmd == "RESET":
            for i in range(self.num_rings):
                self.theta[i] = 0.0
                self.omega[i] = 0.0
        elif cmd == "KICK" and len(parts) == 3:
            ring, impulse = int(parts[1]), float(parts[2])
            if 0 <= ring < self.num_rings:
                self.omega[ring] += impulse
        elif cmd == "DAMP" and len(parts) == 2:
            self.damping = max(0.0, float(parts[1]))
