# AutomatedPipette

Universal computer control for the **Sartorius Picus® 2** electronic
pipette. This project drives the pipette programmatically over a serial
or wireless link so liquid-handling steps (aspirate, dispense,
blow-out) can be scripted instead of triggered by hand — the foundation
for integrating the pipette into automated lab workflows.

> This branch (`main`) treats **USB serial** as the primary transport.
> A `bluetooth-connection` branch documents the same project framed
> around the BLE link.

## The device

The Picus 2 is a rechargeable electronic pipette from Sartorius with an
electronic brake and piston control system, exposed to software through
a JSON command interface over USB serial or Bluetooth Low Energy (BLE).

### Specifications (from the product datasheet)

| Item | Value |
| --- | --- |
| Battery | Li-Polymer, 3.7 V / 350 mAh (≈1 h charge) |
| Pipetting cycles / charge | >1,000 (1-ch ≤1,000 µL); >500 (larger / multichannel) |
| Volume range | 1-ch: 0.5–10,000 µL; 8/12-ch: 0.5–1,200 µL |
| Channels | 1, 8, or 12 |
| Pipetting modes | 8 main modes + 8 advanced functions |
| Memory slots | 20 stored pipetting settings |
| Tip ejection | Electronic |
| Bluetooth | Yes, 2402–2480 MHz |
| Autoclavable lower parts | 121 °C, 20 min, 1 bar |
| Tips | Sartorius Optifit / Safetyspace Filter Tips |

Pipetting modes include Pipetting (forward), Reverse Pipetting, Manual
Pipetting, Multi-Dispensing, Diluting, Sequential Dispensing,
Multi-Aspiration, and Titrate.

### Models

Models are identified in software by `GET_MODEL`. The model determines
the valid volume range, so confirm it before sending motion commands.

| Order no. | Channels | Volume range | Software model |
| --- | --- | --- | --- |
| LH-747021 | 1 | 0.5–10 µL | — |
| LH-747041 | 1 | 5–120 µL | — |
| LH-747061 | 1 | 10–300 µL | — |
| **LH-747081** | **1** | **50–1,000 µL** | **`SINGLE_CHANNEL_1000UL`** |
| LH-747101 | 1 | 100–5,000 µL | — |
| LH-747111 | 1 | 500–10,000 µL | — |
| LH-747321/421 | 8 / 12 | 0.5–10 µL | — |
| LH-747341/441 | 8 / 12 | 5–120 µL | — |
| LH-747361/461 | 8 / 12 | 10–300 µL | — |
| LH-747391/491 | 8 / 12 | 50–1,200 µL | — |

The unit used to develop this project is the **LH-747081** (1-channel,
50–1,000 µL, firmware `CP-7.0`). At nominal 1,000 µL its systematic
error is ±0.45 % and random error 0.15 % (ISO 8655, Optifit tips).

## How the code works

The control logic lives in the `picus2` package (`src/picus2/`). The
pipette speaks the same newline-framed JSON protocol over both links, so
the package separates the *protocol* from the *transport*:

```
your script
    │
    ▼
Picus2Client ──uses──> Transport (abstract)
    │                     ├── SerialTransport  (USB, pyserial)
    │                     └── BleTransport      (BLE, bleak)
    │
    ├── protocol.py   build/parse the JSON line protocol (no I/O)
    └── pipetting.py  forward / reverse / multi-dispense sequences
```

| Module | Responsibility |
| --- | --- |
| `transport.py` | Open a link, write command bytes, deliver each response line. `SerialTransport` runs a reader thread that frames `\r\n` lines onto the event loop; `BleTransport` uses the Nordic UART Service. |
| `protocol.py` | Pure helpers: build `{"no", "data"}` command bytes and parse `ACK` / `BEGIN` / data / `END` responses (no I/O). |
| `client.py` | `Picus2Client`: connect, number commands, await each response, and expose `get_version`, `aspirate`, `blow_out`, etc. |
| `pipetting.py` | High-level techniques built on the client: `forward_pipette`, `reverse_pipette`, `multi_dispense`. |
| `constants.py` | UUIDs, serial defaults, speed limits, result tags. |

A command round-trip is: the client sends `{"no": N, "data": "CMD"}\r\n`,
the device replies with `ACK N`, `BEGIN N`, optional data lines, a result
tag (`OK`, `NOT_ALLOWED`, …), and `END N`. The client matches replies by
the command number `N`, so device chatter cannot corrupt a response.

### Motor-control authorization

Motion commands are blocked until motor control is authorized on the
device. `Picus2Client.enable_motor_control()` performs the full ritual:
it sends `ENABLE_MOTOR_CONTROL 1`, answers the on-screen prompt with the
YES soft key, then sets `AUTO 1` so buffered commands execute without a
physical trigger.

> **Authorize with no tip mounted.** Answering YES with a tip on ejects
> it as a one-time reset. The pipette must also be in a pipetting mode,
> not the mode-selection menu.

## Connecting the pipette

### USB (primary)

1. Connect the pipette to the host with a USB cable and power it on.
2. It enumerates as a CDC-ACM serial port, typically `/dev/ttyACM0`
   (Linux). No pairing is needed.
3. Verify it is the pipette (vendor `24bc:2202`, e.g. serial
   `46980628`) if several serial devices are present.

```python
import asyncio
from picus2 import Picus2Client

async def main():
    async with Picus2Client.over_serial("/dev/ttyACM0") as pipette:
        print(await pipette.get_model())     # SINGLE_CHANNEL_1000UL
        print(await pipette.get_version())   # CP-7.0

asyncio.run(main())
```

### BLE (alternative)

Pair the pipette once through the operating system using the passkey
shown on the device under *Settings → Bluetooth → Bluetooth Passkey*;
the firmware only answers commands over a bonded link. Then:

```python
async with Picus2Client.over_ble("Picus-46980628") as pipette:
    ...
```

> Inside Docker, BLE additionally requires the container to share the
> host network namespace (`--network host`); USB has no such
> requirement. This is why USB is the primary transport here.

## Installation

```bash
python -m venv .venv
.venv/bin/pip install -e .          # needs Python >= 3.14
```

If the host Python is older, run against the sources directly:

```bash
.venv/bin/pip install bleak pyserial
PYTHONPATH=src .venv/bin/python examples/example_usb.py
```

## Example: forward pipetting

```python
async with Picus2Client.over_serial("/dev/ttyACM0") as pipette:
    await pipette.enable_motor_control()      # authorize with NO tip
    await pipette.aspirate(500, speed=7)      # mount + dip first
    await pipette.blow_out(speed=7)           # dispense + return home
    await pipette.disable_motor_control()
```

Runnable scripts:

- `examples/example_usb.py` — read model/version over USB.
- `examples/example_forward.py` — forward pipette over BLE.
- `claude_test/forward_pipetting_usb.py` — interactive real-liquid
  forward pipetting over USB, with pauses for the physical steps.

## Project layout

```
src/picus2/        production control library (transport, client, ...)
tests/             unit tests (protocol, pipetting math, fake transport)
examples/          minimal runnable examples
claude_test/       exploratory / interactive hardware scripts
docs/              Picus 2 manuals, datasheet, command reference
```

## Safety

- Validate any new sequence with an **empty tip** before using liquid.
- Start with small volumes and slow speeds; keep the pipette in view.
- Do not trust a software `OK` alone — confirm the physical motion.
- Confirm the model and its volume range before sending motion commands.

## Documentation

See [`docs/README.md`](docs/README.md) for a guided tour of the Picus 2
manuals: product datasheet, operating instructions, command reference,
and pipetting basics.
