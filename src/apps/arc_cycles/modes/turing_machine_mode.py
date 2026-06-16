"""
Turing Machine 2×2  (IIS 13)

Zwei unabhängige Shift-Register (A und B) mit konfigurierbaren Loop-Längen.
Durch unterschiedliche Loop-Längen entsteht ein sich langsam verschiebender
Phasen-Effekt zwischen den beiden Registern (Steve Reich auf Bit-Ebene).

Layout:
  rings[0] = Register A — Inhalt + Playhead
  rings[1] = Register A — Mutations-Rate + Playhead-Echo
  rings[2] = Register B — Inhalt + Playhead
  rings[3] = Register B — Mutations-Rate + Playhead-Echo

Encoder:
  Ring 0 / 2 : Mutations-Rate des jeweiligen Registers (0–100 %)
  Ring 1 / 3 : Loop-Länge (7 / 8 / 9 / 10 / 11 / 12 / 16 / 24 / 32)

Encoder-Press:
  Ring 0 oder 1 → Register A neu randomisieren + Playhead Reset
  Ring 2 oder 3 → Register B neu randomisieren + Playhead Reset

IIQ:
  rings[0] State 1 : Output-Bit Register A  (5000 = 1, 0 = 0)
  rings[2] State 1 : Output-Bit Register B  (5000 = 1, 0 = 0)
"""

import random
from apps.arc_cycles.mode_base import MultiRingMode

_LOOP_STEPS  = [7, 8, 9, 10, 11, 12, 16, 24, 32]
_REG_SIZE    = 32      # internes Register immer 32 Bit; Loop-Länge bestimmt aktiven Teil
_CLOCK_RATE  = 4.0     # Schritte / Sekunde
_MUT_STEP    = 0.02    # Encoder-Empfindlichkeit Mutations-Rate
_BRIGHT_ON   = 12      # Helligkeit gesetzter Bits
_BRIGHT_OFF  =  1      # Helligkeit gelöschter Bits
_BRIGHT_HEAD = 15      # Helligkeit Playhead


class TuringMachine2x2(MultiRingMode):
    """
    Zwei Shift-Register, Paar A auf rings[0..1], Paar B auf rings[2..3].
    Defaultmäßig: Loop A = 16 Schritte, Loop B = 12 Schritte (LCM = 48).
    """

    def __init__(self, rings: list, arc, arc_offset: int = 0, **kw):
        super().__init__(rings, arc, arc_offset)
        # Zwei Register, je _REG_SIZE Bits
        self._reg  = [
            [random.randint(0, 1) for _ in range(_REG_SIZE)],
            [random.randint(0, 1) for _ in range(_REG_SIZE)],
        ]
        self._head  = [0, 0]
        self._loop  = [16, 12]    # aktive Loop-Längen (7 vs 11 wäre klassisch prime)
        self._mut   = [0.05, 0.05]
        self._acc   = [0.0, 0.0]
        self._out   = [0, 0]      # letztes Output-Bit (für IIQ)
        self._fired = [False, False]

    # ------------------------------------------------------------------ #
    #  Shift-Register-Schritt                                             #
    # ------------------------------------------------------------------ #

    def _step(self, i: int):
        head = self._head[i]
        loop = self._loop[i]
        reg  = self._reg[i]

        # Output = aktuelles Bit am Playhead
        bit = reg[head]
        self._out[i]   = bit
        self._fired[i] = bool(bit)

        # Das Bit, das "am Ende rausfällt", wird neu berechnet
        write_pos = (head + loop - 1) % loop
        if random.random() < self._mut[i]:
            reg[write_pos] = random.randint(0, 1)
        # sonst bleibt es stehen → Loop

        self._head[i] = (head + 1) % loop

    # ------------------------------------------------------------------ #
    #  Update                                                              #
    # ------------------------------------------------------------------ #

    def update(self, dt: float):
        for i in range(2):
            self._acc[i] += dt * _CLOCK_RATE
            while self._acc[i] >= 1.0:
                self._acc[i] -= 1.0
                self._fired[i] = False
                self._step(i)

    # ------------------------------------------------------------------ #
    #  Display                                                             #
    # ------------------------------------------------------------------ #

    def display(self):
        for i in range(2):
            ring_c = self.rings[i * 2]      # Inhalts-Ring
            ring_s = self.rings[i * 2 + 1]  # Status-Ring
            loop   = self._loop[i]
            reg    = self._reg[i]
            head   = self._head[i]
            mut    = self._mut[i]

            phead_led = head * 64 // loop

            # Inhalts-Ring: Bits als gleichmäßige Segmente
            leds_c = [0] * 64
            for bit in range(loop):
                start  = bit * 64 // loop
                end    = (bit + 1) * 64 // loop
                bright = _BRIGHT_ON if reg[bit] else _BRIGHT_OFF
                for l in range(start, end):
                    leds_c[l] = bright
            leds_c[phead_led] = _BRIGHT_HEAD

            # Status-Ring: Mutations-Rate als gefüllter Bogen + Playhead-Echo
            leds_s = [0] * 64
            for l in range(int(mut * 64)):
                leds_s[l] = 5
            leds_s[phead_led] = _BRIGHT_HEAD

            self._send_ring(ring_c, leds_c)
            self._send_ring(ring_s, leds_s)

    # ------------------------------------------------------------------ #
    #  Encoder                                                             #
    # ------------------------------------------------------------------ #

    def on_encoder_turn(self, ring: int, delta: int):
        i     = 0 if ring in self.rings[:2] else 1
        which = self.rings.index(ring) % 2   # 0 = Inhalts-Ring, 1 = Status-Ring

        if which == 0:
            # Inhalts-Ring: Mutations-Rate
            self._mut[i] = max(0.0, min(1.0, self._mut[i] + delta * _MUT_STEP))
        else:
            # Status-Ring: Loop-Länge
            try:
                idx = _LOOP_STEPS.index(self._loop[i])
            except ValueError:
                idx = 4
            idx = max(0, min(len(_LOOP_STEPS) - 1, idx + (1 if delta > 0 else -1)))
            self._loop[i] = _LOOP_STEPS[idx]

    def on_encoder_press(self, ring: int):
        i = 0 if ring in self.rings[:2] else 1
        self._reg[i]  = [random.randint(0, 1) for _ in range(_REG_SIZE)]
        self._head[i] = 0

    def get_iiq_value(self, ring: int, vtype: int) -> int:
        if ring not in self.rings:
            return 0
        i = self.rings.index(ring) // 2   # 0 = Register A, 1 = Register B
        if vtype == 0:  # IIQ x0: Output-Bit (5000=1, 0=0)
            return 5000 if self._out[i] else 0
        if vtype == 1:  # IIQ x1: Mutations-Rate (0–5000)
            return int(self._mut[i] * 5000)
        return 0
