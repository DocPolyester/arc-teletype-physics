/*
 * teletype_bridge.ino  v2.0
 *
 * IIQ-Kommando-Schema (1 Byte, 0-255):
 *   cmd 20..23  → Ring 0, Zustand (cmd - 20)
 *   cmd 30..33  → Ring 1, Zustand (cmd - 30)
 *   cmd 40..43  → Ring 2, Zustand (cmd - 40)
 *   cmd 50..53  → Ring 3, Zustand (cmd - 50)
 *   Formel: ring = (cmd / 10) - 2,  state = cmd % 10
 *
 * Zustände (state = cmd % 10):
 *   0 = Position   (0..63, Arc-Position)
 *   1 = Velocity   (Geschwindigkeit × 100)
 *   2 = Angle      (Winkel × 10, Grad)
 *   3 = Param1     (modusspezifisch)
 *
 * Hinweis: IIS 10-15 sind für Modus-Befehle reserviert (Chaos, Probability,
 * Phase Shift, Turing Machine, Meadowphysics). Deshalb startet IIQ bei 20.
 *
 * Serial RPi → Arduino (34 Bytes):
 *   [0xAA] [32 Bytes Daten] [XOR-Checksum]
 *   Daten: Ring0-Zust0..3, Ring1-Zust0..3, Ring2-Zust0..3, Ring3-Zust0..3
 *   Je Wert: 2 Bytes big-endian int16
 *
 * Serial Arduino → RPi (N+3 Bytes):
 *   [0xBB] [N] [data0..dataN-1] [XOR-Checksum]
 */

#include <Wire.h>

const uint8_t  I2C_ADDR  = 0x31;
const uint32_t BAUD      = 115200;
const uint8_t  N_RINGS   = 4;
const uint8_t  N_STATES  = 4;   // 0=pos 1=vel 2=angle 3=param1

volatile int16_t ring_vals[N_RINGS][N_STATES];

volatile uint8_t req_ring  = 0;
volatile uint8_t req_state = 0;

struct TelCmd {
    uint8_t data[32];
    uint8_t len;
    bool    ready;
};
volatile TelCmd tel_cmd = {{0}, 0, false};

// 32 Datenbytes + 1 Checksum-Byte
uint8_t ser_buf[33];
int     ser_pos = 0;

// ---- Wire-Callbacks -------------------------------------------------------

void onReceive(int numBytes) {
    if (!tel_cmd.ready) {
        tel_cmd.len = 0;
        while (Wire.available()) {
            uint8_t b = Wire.read();
            if (tel_cmd.len < (uint8_t)sizeof(tel_cmd.data))
                tel_cmd.data[tel_cmd.len++] = b;
        }
        if (tel_cmd.len > 0) {
            uint8_t cmd = tel_cmd.data[0];
            if (cmd >= 20 && cmd <= 53) {
                req_ring  = (cmd / 10) - 2;   // 20→0, 30→1, 40→2, 50→3
                req_state = cmd % 10;
                if (req_state >= N_STATES) req_state = 0;
            }
            tel_cmd.ready = true;
        }
    } else {
        while (Wire.available()) Wire.read();
    }
}

void onRequest() {
    uint8_t r   = req_ring  & 0x03;
    uint8_t s   = req_state < N_STATES ? req_state : 0;
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
    Serial.print("TELETYPE_BRIDGE v2.0 addr=0x");
    Serial.println(I2C_ADDR, HEX);
}

// ---- Main Loop -----------------------------------------------------------

void loop() {
    // 1) Teletype-Befehl → RPi weiterleiten
    if (tel_cmd.ready) {
        uint8_t n   = tel_cmd.len;
        uint8_t chk = n;
        for (uint8_t i = 0; i < n; i++) chk ^= tel_cmd.data[i];
        Serial.write((uint8_t)0xBB);
        Serial.write(n);
        Serial.write((const uint8_t *)tel_cmd.data, n);
        Serial.write(chk);
        tel_cmd.ready = false;
    }

    // 2) Ring-Werte vom RPi empfangen
    // Format: [0xAA][32 Bytes][XOR] = 34 Bytes
    // Daten: ring_vals[0][0..3], ring_vals[1][0..3], ..., ring_vals[3][0..3]
    while (Serial.available() > 0) {
        uint8_t b = (uint8_t)Serial.read();

        if (ser_pos == 0) {
            if (b == 0xAA) ser_pos = 1;
            continue;
        }

        ser_buf[ser_pos - 1] = b;
        ser_pos++;

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
