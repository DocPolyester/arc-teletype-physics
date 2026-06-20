/*
 * teletype_bridge.ino  v2.2
 *
 * Fixes vs v2.0:
 *   - IIQ queries (cmd 20-53) no longer occupy the forward-queue.
 *     They only update req_ring/req_state for onRequest(). RPi doesn't need them.
 *     In v2.0 an IIQ would set tel_cmd.ready=true, silently dropping the next
 *     IIS (e.g. IIS 88) if loop() hadn't cleared it yet.
 *   - IIS commands use a 4-entry circular queue so back-to-back IIS commands
 *     (e.g. IIS 14 followed immediately by IIS 88) are never dropped.
 *   - Serial.write uses a single buffer call per packet (less latency).
 *
 * IIQ schema (register byte, 0-255):
 *   20-23 → Ring 0, state 0-3
 *   30-33 → Ring 1, state 0-3
 *   40-43 → Ring 2, state 0-3
 *   50-53 → Ring 3, state 0-3
 *   Formula: ring = (cmd/10)-2, state = cmd%10
 *
 * Serial RPi→Arduino (34 bytes):
 *   [0xAA] [32 bytes data] [XOR checksum]
 *   Data: ring_vals[0][0..3], ring_vals[1][0..3], ... (int16 big-endian)
 *
 * Serial Arduino→RPi (N+3 bytes):
 *   [0xBB] [N] [data0..dataN-1] [XOR checksum]
 */

#include <Wire.h>

const uint8_t  I2C_ADDR  = 0x31;
const uint32_t BAUD      = 115200;
const uint8_t  N_RINGS   = 4;
const uint8_t  N_STATES  = 4;

volatile int16_t ring_vals[N_RINGS][N_STATES];

volatile uint8_t req_ring  = 0;
volatile uint8_t req_state = 0;

// ---- IIS command queue (ISR writes, loop() reads) -------------------------
// 4-entry circular buffer — power of 2 for cheap masking.
// ISR modifies cmd_tail only; loop() modifies cmd_head only → no locking needed.

#define CMD_Q     4
#define CMD_Q_MSK (CMD_Q - 1)

struct CmdEntry {
    uint8_t data[4];
    uint8_t len;
};

volatile CmdEntry cmd_buf[CMD_Q];
volatile uint8_t  cmd_tail = 0;   // ISR: next write slot
         uint8_t  cmd_head = 0;   // loop(): next read slot (non-volatile: only loop() touches it)

// ---- Serial RX state machine ----------------------------------------------
uint8_t ser_buf[33];
int     ser_pos = 0;

// ---- Wire callbacks -------------------------------------------------------

void onReceive(int /*numBytes*/) {
    uint8_t bytes[4];
    uint8_t n = 0;
    while (Wire.available()) {
        uint8_t b = Wire.read();
        if (n < 4) bytes[n] = b;
        n++;
    }
    if (n == 0) return;

    uint8_t cmd = bytes[0];

    if (cmd >= 20 && cmd <= 53) {
        // IIQ register: update req_ring/req_state for onRequest().
        // Do NOT forward to RPi — RPi ignores these anyway.
        req_ring  = (uint8_t)((cmd / 10) - 2);
        req_state = cmd % 10;
        if (req_state >= N_STATES) req_state = 0;
    } else {
        // IIS command: enqueue for forwarding to RPi.
        uint8_t next = (cmd_tail + 1) & CMD_Q_MSK;
        if (next != cmd_head) {          // queue not full
            uint8_t slot = cmd_tail;
            for (uint8_t i = 0; i < n && i < 4; i++)
                cmd_buf[slot].data[i] = bytes[i];
            cmd_buf[slot].len = (n <= 4) ? n : 4;
            cmd_tail = next;             // publish entry (8-bit write = atomic on AVR)
        }
        // if queue full: command dropped, but this requires 4 back-to-back IIS
        // commands before loop() runs — extremely unlikely at any realistic tempo.
    }
}

void onRequest() {
    uint8_t r   = req_ring  & 0x03;
    uint8_t s   = (req_state < N_STATES) ? req_state : 0;
    int16_t val = ring_vals[r][s];
    Wire.write((uint8_t)(val >> 8));
    Wire.write((uint8_t)(val & 0xFF));
}

// ---- Setup ---------------------------------------------------------------

void setup() {
    memset((void *)ring_vals, 0, sizeof(ring_vals));
    Wire.begin(I2C_ADDR);
    Wire.onReceive(onReceive);
    Wire.onRequest(onRequest);
    Serial.begin(BAUD);
    delay(100);
    Serial.print("TELETYPE_BRIDGE v2.2 addr=0x");
    Serial.println(I2C_ADDR, HEX);
}

// ---- Main Loop -----------------------------------------------------------

void loop() {
    // 1) Forward queued IIS commands to RPi via Serial
    while (cmd_head != cmd_tail) {
        uint8_t n = cmd_buf[cmd_head].len;
        uint8_t pkt[7];          // BB + len + up to 4 data bytes + chk
        pkt[0] = 0xBB;
        pkt[1] = n;
        uint8_t chk = n;
        for (uint8_t i = 0; i < n; i++) {
            uint8_t b = cmd_buf[cmd_head].data[i];
            pkt[2 + i] = b;
            chk ^= b;
        }
        pkt[2 + n] = chk;
        Serial.write(pkt, 3 + n);           // single buffered write
        cmd_head = (cmd_head + 1) & CMD_Q_MSK;
    }

    // 2) Receive ring_vals state from RPi
    // Format: [0xAA][32 bytes data][XOR checksum] = 34 bytes total
    //
    // Progressive state-0 update: TX layout is R0[s0,s1,s2,s3], R1[...], R2[...], R3[...]
    // so ring r state 0 is at ser_buf[r*8 .. r*8+1].
    // We update ring_vals[r][0] (fired state) as soon as those 2 bytes arrive,
    // without waiting for the full 34-byte packet. This cuts the IIQ read latency
    // from ~3.8ms (full packet) to ~1.0-3.1ms per ring — Teletype IIQ reads happen
    // at ~1.4/2.8/4.2/5.6ms after IIS 88, so all rings get fresh state in time.
    while (Serial.available() > 0) {
        uint8_t b = (uint8_t)Serial.read();

        if (ser_pos == 0) {
            if (b == 0xAA) ser_pos = 1;
            continue;
        }

        ser_buf[ser_pos - 1] = b;
        ser_pos++;

        // After receiving the low byte of ring r state 0, update ring_vals[r][0].
        // Ring r state 0 lo byte is at ser_buf[r*8+1], stored when ser_pos reaches r*8+3.
        for (uint8_t r = 0; r < N_RINGS; r++) {
            if (ser_pos == (uint8_t)(r * 8 + 3)) {
                uint8_t idx = r * 8;
                int16_t val = (int16_t)(((uint16_t)ser_buf[idx] << 8) | ser_buf[idx + 1]);
                noInterrupts();
                ring_vals[r][0] = val;
                interrupts();
            }
        }

        if (ser_pos == 34) {
            uint8_t chk = 0;
            for (int i = 0; i < 32; i++) chk ^= ser_buf[i];
            if (chk == ser_buf[32]) {
                noInterrupts();
                for (uint8_t r = 0; r < N_RINGS; r++) {
                    for (uint8_t s = 0; s < N_STATES; s++) {
                        uint8_t idx = (r * N_STATES + s) * 2;
                        ring_vals[r][s] = (int16_t)(
                            ((uint16_t)ser_buf[idx] << 8) | ser_buf[idx + 1]);
                    }
                }
                interrupts();
            }
            ser_pos = 0;
        }
    }
}
