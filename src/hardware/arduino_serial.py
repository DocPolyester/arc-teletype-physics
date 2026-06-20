"""
Arduino Serial I2C Bridge — Ersatz für i2c_slave.py (pigpio BSC).

Statt des BCM2835 BSC-Slave nutzt ein Arduino Nano V3.0 (USB an RPi)
als I2C-Slave auf dem Teletype-Bus. Der Arduino antwortet auf IIQ-Anfragen
mit den Ring-Werten die er ~60 Hz vom RPi via USB-Serial empfängt.

Hardware:
  Arduino Nano V3.0 → USB → /dev/ttyUSB1 (RPi)
  Arduino A4 (SDA) + A5 (SCL) → Teletype I2C Bus  (4.7kΩ Pull-ups nötig)
  I2C Adresse: 0x31 (49 dezimal → Teletype: IIA 49)

Serial-Protokoll RPi→Arduino (34 Bytes):
  [0xAA][32 Bytes: 4 Ringe × 4 Zustände × int16 big-endian][xor_chk]

Serial-Protokoll Arduino→RPi (N+3 Bytes):
  [0xBB][N][data0..dataN-1][xor_chk]

IIS-Befehle (alle Ringe, Single-Ring-Modi):
  IIS 49 1..9   → Moduswechsel alle Ringe (1=cycles .. 9=drunk)
  IIS 49 10     → Chaos (alle Ringe)
  IIS 49 11     → Probability (alle Ringe)

IIS-Befehle (Multi-Ring-Modi):
  IIS 49 12     → Phase Shift (2×2 Ringe)
  IIS 49 13     → Turing Machine 2×2 (4 Ringe)
  IIS 49 14     → Meadowphysics (4 Ringe, Kaskaden-Zähler-Netzwerk)
  IIS 49 15     → reserviert
  IIS 49 88     → Clock Tick (externer Takt für Clock-Div/Mul)

IIS-Befehle (einzelner Ring):
  IIS 49 101..111 → Ring 1 Modus 1..11
  IIS 49 201..211 → Ring 2 Modus 1..11
  IIS 49 301..311 → Ring 3 Modus 1..11
  IIS 49 401..411 → Ring 4 Modus 1..11
  (Teletype sendet 16-bit; Decode: ring = val//100 - 1, mode = val%100)

IIS-Befehle (System):
  IIS 49 90/91  → ARC-Ausrichtung (0°/270°)
  IIS 49 99     → RPi herunterfahren

IIQ-Abfragen (Teletype schreibt Register, liest 2 Bytes int16):
  IIQ 49 20..23 → Ring 0, Zustand 0..3
  IIQ 49 30..33 → Ring 1, Zustand 0..3
  IIQ 49 40..43 → Ring 2, Zustand 0..3
  IIQ 49 50..53 → Ring 3, Zustand 0..3
  Zustände: 0=Position(0-5000)  1=Velocity(±5000)  2=Angle(±5000)  3=Param1(0-5000)
  (Hinweis: Startet bei 20 statt 10, da IIS 10-15 für Modi reserviert sind)
"""

import logging
import math
import serial
import struct
import subprocess
import threading
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.arc_cycles.main import ArcCyclesApp

logger = logging.getLogger(__name__)

MODE_NAMES = [
    "cycles", "pendulum", "gravity", "spring", "orbit", "swing",
    "euclidean", "bounce", "drunk", "chaos", "probability",
]

VTYPE_POSITION = 0
VTYPE_VELOCITY = 1
VTYPE_ANGLE    = 2
VTYPE_PARAM1   = 3

TX_HEADER = 0xAA
RX_HEADER = 0xBB
BAUD      = 115200
N_STATES  = 4   # 0=pos 1=vel 2=angle 3=param1


class ArduinoSerialHandler:
    """
    Arduino Nano USB-Serial I2C Bridge.

    Nutzung:
        handler = ArduinoSerialHandler(port="/dev/ttyUSB1")
        handler.set_app(app)
        handler.start()
        # Im Physics-Loop (~60 Hz):
        handler.update_state(app)
        handler.stop()
    """

    def __init__(self, port: str = "/dev/ttyUSB1", address: int = 0x31):
        self.port    = port
        self.address = address

        self._app: Optional["ArcCyclesApp"] = None
        self._ser: Optional[serial.Serial]  = None
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False

        self._vtype       = VTYPE_POSITION
        self._vring       = 0xF
        self._pending_cmd: Optional[int] = None
        self._pending_hi:  Optional[int] = None
        self._last_send   = 0.0

    def set_app(self, app: "ArcCyclesApp"):
        self._app = app

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def start(self):
        self._ser = serial.Serial(self.port, BAUD, timeout=0.05)
        # Arduino resettet beim Öffnen der Serial-Verbindung → 2s warten
        time.sleep(2.0)
        self._ser.reset_input_buffer()

        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True,
                                           name="arduino-rx")
        self._rx_thread.start()
        logger.info(
            f"Arduino I2C Bridge: {self.port} @ {BAUD} baud  "
            f"I2C-Adresse=0x{self.address:02x}"
        )

    def stop(self):
        self._running = False
        if self._ser and self._ser.is_open:
            self._ser.close()
        logger.info("Arduino I2C Bridge gestoppt")

    # ------------------------------------------------------------------ #
    #  TX-Update – im Physics-Loop aufrufen (~60 Hz)                      #
    # ------------------------------------------------------------------ #

    def update_state(self, app: "ArcCyclesApp"):
        """Sendet aktuelle Ring-Werte an den Arduino (max 60 Hz)."""
        now = time.time()
        if now - self._last_send < 0.016:
            return
        self._last_send = now

        if not (self._ser and self._ser.is_open):
            return

        tx = self._build_tx(app)
        self._send_packet(tx)

    def _build_tx(self, app: "ArcCyclesApp") -> bytes:
        """32-Byte TX-Puffer: 4 Ringe × 4 Zustände als int16 big-endian.
        Layout: ring0[pos,vel,ang,p1], ring1[...], ring2[...], ring3[...]"""
        buf = bytearray(32)
        for r in range(4):
            for s in range(N_STATES):
                val = self._get_value(app, r, s)
                val = max(-32768, min(32767, val))
                struct.pack_into(">h", buf, (r * N_STATES + s) * 2, val)
        return bytes(buf)

    def _send_packet(self, data: bytes):
        """Sendet [0xAA][N Bytes Daten][XOR-Checksum]."""
        chk = 0
        for b in data:
            chk ^= b
        pkt = bytes([TX_HEADER]) + data + bytes([chk])
        try:
            self._ser.write(pkt)
        except serial.SerialException as e:
            logger.error(f"Serial write: {e}")

    # ------------------------------------------------------------------ #
    #  RX – Arduino→RPi (Teletype-Befehle werden weitergeleitet)          #
    # ------------------------------------------------------------------ #

    def _rx_loop(self):
        """Liest Teletype-Befehle die der Arduino per 0xBB-Protokoll schickt."""
        state   = "IDLE"
        cmd_len = 0
        cmd_buf: list[int] = []

        while self._running:
            try:
                if not (self._ser and self._ser.is_open):
                    time.sleep(0.1)
                    continue
                raw = self._ser.read(1)
                if not raw:
                    continue
                b = raw[0]

                if state == "IDLE":
                    if b == RX_HEADER:
                        state = "LEN"
                    elif b in (0x54, 0x45):  # 'T' oder 'E' = startup-Text
                        state = "TEXT"

                elif state == "TEXT":
                    if b == 0x0A:
                        state = "IDLE"

                elif state == "LEN":
                    cmd_len = b
                    cmd_buf = []
                    if cmd_len == 0:
                        state = "IDLE"
                    else:
                        state = "DATA"

                elif state == "DATA":
                    cmd_buf.append(b)
                    if len(cmd_buf) == cmd_len:
                        state = "CHK"

                elif state == "CHK":
                    chk = cmd_len
                    for x in cmd_buf:
                        chk ^= x
                    if chk == b:
                        self._handle_rx(bytes(cmd_buf))
                    else:
                        logger.warning("RX Checksum-Fehler")
                    state = "IDLE"

            except serial.SerialException as e:
                logger.error(f"RX loop serial error: {e}")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"RX loop: {e}")
                time.sleep(0.01)

    # ------------------------------------------------------------------ #
    #  Befehlsverarbeitung                                                #
    # ------------------------------------------------------------------ #

    def _handle_rx(self, data: bytes):
        i = 0
        while i < len(data):
            if i + 1 >= len(data):
                self._dispatch_ring_select(data[i])
                break
            hi = data[i]
            lo = data[i + 1]
            self._dispatch(hi, lo)
            i += 2

    def _dispatch_ring_select(self, cmd: int):
        # ── All-ring mode switch ─────────────────────────────────────────
        # IIS 1-11: modes 1-11 (IIQ registers shifted to 20-53, no collision)
        if 1 <= cmd <= len(MODE_NAMES):
            if self._app:
                name = MODE_NAMES[cmd - 1]
                self._app.set_mode(name)
                logger.info(f"IIS Mode → {name}")
        elif cmd == 12:
            if self._app:
                self._app.activate_multi_mode("phase_shift", [[0, 1], [2, 3]])
                logger.info("IIS 12: Phase Shift aktiviert (Ringe 0+1 / 2+3)")
        elif cmd == 13:
            if self._app:
                self._app.activate_multi_mode("turing_2x2", [[0, 1, 2, 3]])
                logger.info("IIS 13: Turing Machine 2×2 aktiviert")
        elif cmd == 14:
            if self._app:
                self._app.activate_multi_mode("meadowphysics", [[0, 1, 2, 3]])
                logger.info("IIS 14: Meadowphysics aktiviert (Ringe 0–3)")
        elif cmd == 15:
            logger.debug("IIS 15: reserviert")
        elif cmd == 88:
            logger.debug("IIS 88: Clock Tick")
        # ── System ──────────────────────────────────────────────────────
        elif cmd == 90 and self._app:
            self._app.set_arc_orientation(0)
        elif cmd == 91 and self._app:
            self._app.set_arc_orientation(48)
        elif cmd == 99:
            logger.info("IIS: RPi Shutdown angefordert")
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])

    def _dispatch(self, hi: int, lo: int):
        app = self._app

        if self._pending_cmd is not None:
            self._dispatch_second_byte(hi, lo)
            return

        # Per-Ring Modus: IIS 1xx / 2xx / 3xx / 4xx (16-bit, alle 11 Modi)
        # Teletype sendet 16-bit → Arduino leitet hi+lo weiter
        # Decode: ring = val//100 - 1,  mode = val%100
        full_val = (hi << 8) | lo
        ring     = full_val // 100 - 1
        mode_idx = full_val % 100
        if app and 0 <= ring <= 3 and 1 <= mode_idx <= len(MODE_NAMES):
            name = MODE_NAMES[mode_idx - 1]
            app.set_ring_mode(ring, name)
            logger.info(f"IIS Ring {ring + 1} → {name}")
            return

        cmd = hi

        if cmd == 0x00:
            # Standard-Einzel-Byte-Befehle (lo = Wert 1-99)
            self._dispatch_ring_select(lo)
            return

        elif cmd == 0x10 and app:
            if 0 <= lo < len(MODE_NAMES):
                app.set_mode(MODE_NAMES[lo])
                logger.info(f"I2C: Mode → {MODE_NAMES[lo]}")

        elif cmd == 0x20:
            self._pending_cmd = 0x20
            self._pending_hi  = lo

        elif cmd == 0x22 and app:
            ring = (lo >> 4) & 0x3
            amp  = (lo & 0x0F) * 2
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "pendulum":
                app.ring_instances[ring].teletype_command(f"AMP 0 {amp}")

        elif cmd == 0x23 and app:
            ring   = (lo >> 4) & 0x3
            center = lo & 0x3F
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "pendulum":
                app.ring_instances[ring].centers[0] = center

        elif cmd == 0x24 and app:
            for r, name in enumerate(app.ring_mode_names):
                if name == "pendulum":
                    app.ring_instances[r].teletype_command("RESET")

        elif cmd == 0x30 and app:
            strength = lo / 10.0
            for r, name in enumerate(app.ring_mode_names):
                if name == "gravity":
                    app.ring_instances[r].gravity_strength = max(0, min(10, strength))

        elif cmd == 0x31 and app:
            for r, name in enumerate(app.ring_mode_names):
                if name == "gravity":
                    app.ring_instances[r].teletype_command("RESET")

        elif cmd == 0x40 and app:
            ring = (lo >> 4) & 0x3
            k    = (lo & 0x0F) / 2.0
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "spring":
                app.ring_instances[ring].teletype_command(f"K 0 {k:.1f}")

        elif cmd == 0x41 and app:
            ring   = (lo >> 6) & 0x3
            center = lo & 0x3F
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "spring":
                app.ring_instances[ring].teletype_command(f"CENTER 0 {center}")

        elif cmd == 0x42 and app:
            for r, name in enumerate(app.ring_mode_names):
                if name == "spring":
                    app.ring_instances[r].teletype_command("RESET")

        elif cmd == 0x50 and app:
            ring = (lo >> 6) & 0x3
            pos  = lo & 0x3F
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "cycles":
                app.ring_instances[ring].teletype_command(f"POS 0 {pos}")

        elif cmd == 0x51:
            self._pending_cmd = 0x51
            self._pending_hi  = lo

        elif cmd == 0x53 and app:
            for r, name in enumerate(app.ring_mode_names):
                if name == "cycles":
                    app.ring_instances[r].teletype_command("RESET")

        elif cmd == 0x60:
            self._pending_cmd = 0x60
            self._pending_hi  = lo

        elif cmd == 0x62 and app:
            ring   = (lo >> 6) & 0x3
            radius = lo & 0x1F
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "orbit":
                app.ring_instances[ring].teletype_command(f"RADIUS 0 {radius}")

        elif cmd == 0x63 and app:
            ring  = (lo >> 4) & 0x3
            count = max(1, min(8, lo & 0x0F))
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "orbit":
                app.ring_instances[ring].teletype_command(f"PARTICLES 0 {count}")

        elif cmd == 0x64 and app:
            for r, name in enumerate(app.ring_mode_names):
                if name == "orbit":
                    app.ring_instances[r].teletype_command("RESET")

        elif cmd == 0x70:
            self._pending_cmd = 0x70
            self._pending_hi  = lo

        elif cmd == 0x72 and app:
            damp = lo / 50.0
            for r, name in enumerate(app.ring_mode_names):
                if name == "swing":
                    app.ring_instances[r].damping = max(0.0, damp)

        elif cmd == 0x73 and app:
            for r, name in enumerate(app.ring_mode_names):
                if name == "swing":
                    app.ring_instances[r].teletype_command("RESET")

        else:
            logger.debug(f"Unbekannter Befehl hi=0x{hi:02x} lo=0x{lo:02x}")

    def _dispatch_second_byte(self, hi: int, lo: int):
        cmd      = self._pending_cmd
        first_lo = self._pending_hi
        self._pending_cmd = None
        self._pending_hi  = None
        app = self._app
        if not app:
            return

        if cmd == 0x20:
            period_ms = ((first_lo & 0xFF) << 8) | lo
            ring      = (first_lo >> 4) & 0x3
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "pendulum":
                app.ring_instances[ring].teletype_command(f"PERIOD 0 {period_ms}")

        elif cmd == 0x51:
            ring  = (first_lo >> 4) & 0x3
            speed = struct.unpack(">h", bytes([first_lo & 0x0F, lo]))[0]
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "cycles":
                app.ring_instances[ring].teletype_command(f"SPEED 0 {speed}")

        elif cmd == 0x60:
            ring      = (first_lo >> 4) & 0x3
            period_ms = ((first_lo & 0x0F) << 8) | lo
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "orbit":
                app.ring_instances[ring].teletype_command(f"PERIOD 0 {period_ms}")

        elif cmd == 0x70:
            ring    = (first_lo >> 4) & 0x3
            impulse = struct.unpack(">h", bytes([first_lo & 0x0F, lo]))[0] / 100.0
            if 0 <= ring < app.num_rings and app.ring_mode_names[ring] == "swing":
                app.ring_instances[ring].teletype_command(f"KICK 0 {impulse:.2f}")

    # ------------------------------------------------------------------ #
    #  Physics value readout (per-ring instance, always internal index 0) #
    # ------------------------------------------------------------------ #

    def _get_value(self, app, ring: int, vtype: int) -> int:
        # Multi-ring modes liefern eigene IIQ-Werte
        if getattr(app, 'ring_claimed_by', None) and app.ring_claimed_by[ring] == 'multi':
            for g in app.multi_ring_groups:
                if ring in g.rings:
                    return g.get_iiq_value(ring, vtype)
            return 0
        if vtype == VTYPE_POSITION: return self._get_position(app, ring)
        if vtype == VTYPE_VELOCITY: return self._get_velocity(app, ring)
        if vtype == VTYPE_ANGLE:    return self._get_angle(app, ring)
        if vtype == VTYPE_PARAM1:   return self._get_param1(app, ring)
        return 0

    def _get_position(self, app, ring: int) -> int:
        """Arc-Position (0–63) skaliert auf 0–5000."""
        try:
            inst = app.ring_instances[ring]
            name = app.ring_mode_names[ring]
            if name == "cycles":
                raw = int(inst.positions[0]) % 64
            elif name == "swing":
                raw = int(round(inst.CENTER + inst.theta[0] * inst.SCALE)) % 64
            elif name == "orbit":
                raw = int(inst.centers[0]) % 64
            elif name == "euclidean":
                raw = inst._head[0] * 64 // max(1, inst.n[0])
            elif name == "bounce":
                raw = int(round(inst.position[0])) % 64
            elif name == "drunk":
                raw = int(round(inst.position[0])) % 64
            elif name == "chaos":
                raw = int((inst._x[0] + 25.0) * 63.0 / 50.0) % 64
            elif name == "probability":
                raw = int(round(inst.probability[0] * 63))
            else:
                raw = int(inst.physics.rings[0][0].position) % 64
            return raw * 5000 // 63
        except Exception:
            return 0

    def _get_velocity(self, app, ring: int) -> int:
        """Geschwindigkeit skaliert auf ±5000."""
        try:
            inst = app.ring_instances[ring]
            name = app.ring_mode_names[ring]
            if name == "cycles":
                return int(inst.speeds[0] * 2500)
            if name == "swing":
                return int(inst.omega[0] * 1592)
            if name == "orbit":
                return int(inst.angular_velocities[0] * 1592)
            if name == "bounce":
                return int(inst.velocity[0] * 100)
            if name == "drunk":
                return int(inst._last_dir[0] * inst.step_size[0] * 100)
            if name == "chaos":
                return int(inst._y[0] * 100)
            if name == "euclidean":
                # 5000 = triggered this frame, 0 = not
                return 5000 if inst._triggered[0] else 0
            if name == "probability":
                return 5000 if inst._fired[0] else 0
            return int(inst.physics.rings[0][0].velocity * 2500)
        except Exception:
            return 0

    def _get_angle(self, app, ring: int) -> int:
        """Winkel skaliert auf ±5000 (±π/2 = ±5000). Für neue Modi: bounce=bounce-flag, chaos=Z-Wert."""
        HALF_PI = math.pi / 2
        try:
            inst = app.ring_instances[ring]
            name = app.ring_mode_names[ring]
            if name == "swing":
                return int(inst.theta[0] * 5000 / HALF_PI)
            if name == "pendulum":
                pos    = inst.physics.rings[0][0].position
                center = inst.centers[0]
                amp    = max(1, inst.amplitudes[0])
                ratio  = max(-1.0, min(1.0, (pos - center) / amp))
                return int(math.asin(ratio) * 5000 / HALF_PI)
            if name == "bounce":
                return 5000 if inst._bounced[0] else 0
            if name == "chaos":
                return int(inst._z[0] * 100)
        except Exception:
            pass
        return 0

    def _get_param1(self, app, ring: int) -> int:
        """Modusspezifischer Parameter skaliert auf 0–5000."""
        try:
            inst = app.ring_instances[ring]
            name = app.ring_mode_names[ring]
            if name == "pendulum":
                return int(inst.periods[0] * 1000)
            if name == "gravity":
                return int(inst.gravity_strength * 500)
            if name == "spring":
                return int(inst.spring_constant[0] * 1000)
            if name == "orbit":
                return int(inst.periods[0] * 1000)
            if name == "swing":
                return int(inst.damping * 2500)
            if name == "euclidean":
                return int(inst.k[0] * 5000 // max(1, inst.n[0]))
            if name == "bounce":
                return int(max(0.0, inst.position[0]) * 5000 // 63)
            if name == "drunk":
                return int(inst.step_size[0] * 312)  # 0–16 → 0–5000
            if name == "chaos":
                return int(inst.rho[0] * 5000 // 60)
            if name == "probability":
                return int(inst.probability[0] * 5000)
        except Exception:
            return 0
        return 0
