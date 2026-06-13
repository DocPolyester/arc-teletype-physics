# Third-Party Licenses

This project uses the following open-source libraries. Their licenses are reproduced below.

---

## python-osc

**Used for:** OSC communication with monome serialosc (encoder events, LED control)  
**PyPI:** https://pypi.org/project/python-osc/  
**Repository:** https://github.com/attwad/python-osc  
**Author:** Florian Lary  

```
The Unlicense

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the software
to the public domain.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
```

---

## pyserial

**Used for:** USB serial communication with Arduino Nano (I2C bridge)  
**PyPI:** https://pypi.org/project/pyserial/  
**Repository:** https://github.com/pyserial/pyserial  
**Author:** Chris Liechti  

```
BSD 3-Clause License

Copyright (c) 2001-2020 Chris Liechti <cliechti@gmx.net>
All Rights Reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## PyYAML

**Used for:** Parsing the `config.yaml` configuration file  
**PyPI:** https://pypi.org/project/PyYAML/  
**Repository:** https://github.com/yaml/pyyaml  
**Author:** Kirill Simonov  

```
MIT License

Copyright (c) 2017-2021 Ingy döt Net
Copyright (c) 2006-2016 Kirill Simonov

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Arduino Wire Library

**Used for:** I2C slave communication on the Arduino Nano (teletype_bridge firmware)  
**Repository:** https://github.com/arduino/ArduinoCore-avr  
**Author:** Arduino LLC  

```
GNU Lesser General Public License v2.1

The Wire library is part of the Arduino AVR core and is licensed under
the GNU Lesser General Public License version 2.1 or later.
Full license text: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html

This project uses the Wire library as a dynamically linked component
(compiled and linked by the Arduino toolchain). The LGPL permits use
of the library in non-GPL projects provided the library itself remains
replaceable.
```

---

## serialosc (OSC Protocol)

**Used for:** Device discovery and OSC message routing for monome Arc  
**Note:** No monome source code is included in this project. This project
communicates with the `serialosc` daemon (installed separately on the host)
via its documented OSC protocol. The OSC endpoint names (`/ring/set`,
`/ring/map`, `/enc/delta`, etc.) follow the monome serialosc specification.  
**Protocol documentation:** https://monome.org/docs/serialosc/osc/  
**serialosc repository:** https://github.com/monome/serialosc (ISC License, monome)

---

## Hardware Acknowledgements

- **monome Arc** — https://monome.org — OSC-based rotary encoder device
- **Monome Teletype** — https://monome.org/docs/teletype/ — Algorithmic sequencer / I2C controller
- **Arduino Nano V3.0** (ATmega328P) — https://arduino.cc — I2C slave bridge firmware platform
