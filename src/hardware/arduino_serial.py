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

IIS-Befehle (Teletype schreibt an Arduino, kein Read):
  IIS 49 1..6  → Moduswechsel (1=cycles 2=pendulum 3=gravity 4=spring 5=orbit 6=swing)
  IIS 49 99    → RPi herunterfahren

IIQ-Abfragen (Teletype schreibt Register, liest 2 Bytes int16):
  IIQ 49 10..19 → Ring 0, Zustand 0..9
  IIQ 49 20..29 → Ring 1, Zustand 0..9
  IIQ 49 30..39 → Ring 2, Zustand 0..9
  IIQ 49 40..49 → Ring 3, Zustand 0..9
  Zustände: 0=Position(0-5000)  1=Velocity(±5000)  2=Angle(±5000)  3=Param1(0-5000)
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

MODE_NAMES = ["cycles", "pendulum", "gravity", "spring", "orbit", "swing"]

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
                    # Startup-String lesen bis Newline
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
        # Einzel-Byte IIS (falls Teletype 1 Byte sendet)
        if 1 <= cmd <= 6:
            if self._app:
                self._app.set_mode(MODE_NAMES[cmd - 1])
                logger.info(f"IIS Mode → {MODE_NAMES[cmd - 1]}")
        elif cmd == 90 and self._app:
            self._app.set_arc_orientation(0)
        elif cmd == 91 and self._app:
            self._app.set_arc_orientation(48)
        elif cmd == 99:
            logger.info("IIS: RPi Shutdown angefordert")
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
        elif 0 <= cmd <= 3:
            self._vring = cmd

    def _dispatch(self, hi: int, lo: int):
        app = self._app

        if self._pending_cmd is not None:
            self._dispatch_second_byte(hi, lo)
            return

        cmd = hi

        if cmd == 0x00:
            # Zwei-Byte IIS: hi=0x00, lo = Befehlswert
            if 1 <= lo <= 6 and app:
                app.set_mode(MODE_NAMES[lo - 1])
                logger.info(f"IIS Mode → {MODE_NAMES[lo - 1]}")
            elif lo == 90 and app:
                app.set_arc_orientation(0)
            elif lo == 91 and app:
                app.set_arc_orientation(48)   # 270° = 48/64 LEDs
            elif lo == 99:
                logger.info("IIS: RPi Shutdown angefordert")
                subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])

        elif cmd == 0x01:
            self._vtype = (lo >> 4) & 0x0F
            self._vring = lo & 0x0F
            logger.debug(f"SELECT vtype={self._vtype} ring={self._vring:#x}")

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
            app.on_teletype_command(f"PEND.AMP {ring} {amp}")

        elif cmd == 0x23 and app:
            ring   = (lo >> 4) & 0x3
            center = lo & 0x3F
            mode   = app.modes.get("pendulum")
            if mode and 0 <= ring < 4:
                mode.centers[ring] = center

        elif cmd == 0x24 and app:
            app.on_teletype_command("PEND.RESET")

        elif cmd == 0x30 and app:
            app.on_teletype_command(f"GRAV.STRENGTH {lo / 10.0:.1f}")

        elif cmd == 0x31 and app:
            app.on_teletype_command("GRAV.RESET")

        elif cmd == 0x40 and app:
            ring = (lo >> 4) & 0x3
            k    = (lo & 0x0F) / 2.0
            app.on_teletype_command(f"SPRING.K {ring} {k:.1f}")

        elif cmd == 0x41 and app:
            ring   = (lo >> 6) & 0x3
            center = lo & 0x3F
            app.on_teletype_command(f"SPRING.CENTER {ring} {center}")

        elif cmd == 0x42 and app:
            app.on_teletype_command("SPRING.RESET")

        elif cmd == 0x50 and app:
            ring = (lo >> 6) & 0x3
            pos  = lo & 0x3F
            app.on_teletype_command(f"CYCLES.POS {ring} {pos}")

        elif cmd == 0x51:
            self._pending_cmd = 0x51
            self._pending_hi  = lo

        elif cmd == 0x53 and app:
            app.on_teletype_command("CYCLES.RESET")

        elif cmd == 0x60:
            self._pending_cmd = 0x60
            self._pending_hi  = lo

        elif cmd == 0x62 and app:
            ring   = (lo >> 6) & 0x3
            radius = lo & 0x1F
            app.on_teletype_command(f"ORBIT.RADIUS {ring} {radius}")

        elif cmd == 0x63 and app:
            ring  = (lo >> 4) & 0x3
            count = max(1, min(8, lo & 0x0F))
            app.on_teletype_command(f"ORBIT.PARTICLES {ring} {count}")

        elif cmd == 0x64 and app:
            app.on_teletype_command("ORBIT.RESET")

        elif cmd == 0x70:
            self._pending_cmd = 0x70
            self._pending_hi  = lo

        elif cmd == 0x72 and app:
            app.on_teletype_command(f"SWING.DAMP {lo / 50.0:.2f}")

        elif cmd == 0x73 and app:
            app.on_teletype_command("SWING.RESET")

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
            app.on_teletype_command(f"PEND.PERIOD {ring} {period_ms}")

        elif cmd == 0x51:
            ring  = (first_lo >> 4) & 0x3
            speed = struct.unpack(">h", bytes([first_lo & 0x0F, lo]))[0]
            app.on_teletype_command(f"CYCLES.SPEED {ring} {speed}")

        elif cmd == 0x60:
            ring      = (first_lo >> 4) & 0x3
            period_ms = ((first_lo & 0x0F) << 8) | lo
            app.on_teletype_command(f"ORBIT.PERIOD {ring} {period_ms}")

        elif cmd == 0x70:
            ring    = (first_lo >> 4) & 0x3
            impulse = struct.unpack(">h", bytes([first_lo & 0x0F, lo]))[0] / 100.0
            app.on_teletype_command(f"SWING.KICK {ring} {impulse:.2f}")

    # ------------------------------------------------------------------ #
    #  Physik-Werte auslesen                                               #
    # ------------------------------------------------------------------ #

    def _get_value(self, app, ring: int, vtype: int) -> int:
        if vtype == VTYPE_POSITION: return self._get_position(app, ring)
        if vtype == VTYPE_VELOCITY: return self._get_velocity(app, ring)
        if vtype == VTYPE_ANGLE:    return self._get_angle(app, ring)
        if vtype == VTYPE_PARAM1:   return self._get_param1(app, ring)
        return 0

    def _get_position(self, app, ring: int) -> int:
        """Arc-Position (0–63) skaliert auf 0–5000."""
        mode = app.current_mode
        name = app.current_mode_name
        try:
            if name == "cycles":
                raw = int(mode.positions[ring]) % 64
            elif name == "swing":
                raw = int(round(mode.CENTER + mode.theta[ring] * mode.SCALE)) % 64
            elif name == "orbit":
                raw = int(mode.centers[ring]) % 64
            else:
                raw = int(mode.physics.rings[ring][0].position) % 64
            return raw * 5000 // 63
        except Exception:
            return 0

    def _get_velocity(self, app, ring: int) -> int:
        """Geschwindigkeit skaliert auf ±5000."""
        mode = app.current_mode
        name = app.current_mode_name
        try:
            if name == "cycles":
                # speeds ±2.0 pos/frame → ±5000
                return int(mode.speeds[ring] * 2500)
            if name == "swing":
                # omega ±π rad/s typisch → ±5000
                return int(mode.omega[ring] * 1592)
            if name == "orbit":
                return int(mode.angular_velocities[ring] * 1592)
            # Partikel-velocity ±2 pos/frame typisch → ±5000
            return int(mode.physics.rings[ring][0].velocity * 2500)
        except Exception:
            return 0

    def _get_angle(self, app, ring: int) -> int:
        """Winkel skaliert auf ±5000 (±π/2 = ±5000)."""
        mode = app.current_mode
        name = app.current_mode_name
        HALF_PI = math.pi / 2
        try:
            if name == "swing":
                # theta ±π/2 → ±5000
                return int(mode.theta[ring] * 5000 / HALF_PI)
            if name == "pendulum":
                pos    = mode.physics.rings[ring][0].position
                center = mode.centers[ring]
                amp    = max(1, mode.amplitudes[ring])
                ratio  = max(-1.0, min(1.0, (pos - center) / amp))
                return int(math.asin(ratio) * 5000 / HALF_PI)
        except Exception:
            pass
        return 0

    def _get_param1(self, app, ring: int) -> int:
        """Modusspezifischer Parameter skaliert auf 0–5000."""
        mode = app.current_mode
        name = app.current_mode_name
        try:
            if name == "pendulum":
                # periods in Sekunden (0.5–5s) → ms (500–5000)
                return int(mode.periods[ring] * 1000)
            if name == "gravity":
                # gravity_strength 0–10 → 0–5000
                return int(mode.gravity_strength * 500)
            if name == "spring":
                # spring_constant 0.1–5.0 → 100–5000
                return int(mode.spring_constant[ring] * 1000)
            if name == "orbit":
                return int(mode.periods[ring] * 1000)
            if name == "swing":
                # damping 0–2.0 → 0–5000
                return int(mode.damping * 2500)
        except Exception:
            return 0
        return 0
