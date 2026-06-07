# AutomatedPipette (Bluetooth connection)

Universal computer control for the **Sartorius Picus® 2** electronic
pipette. This project drives the pipette programmatically so
liquid-handling steps (aspirate, dispense, blow-out) can be scripted
instead of triggered by hand.

> **This is the `bluetooth-connection` branch.** It preserves the
> original **BLE-only** implementation, where `Picus2Client` connects
> over Bluetooth Low Energy via `bleak`. The `main` branch generalizes
> this into a transport abstraction that also speaks USB serial — prefer
> `main` for new work; this branch is the wireless-only reference.

## The device

The Picus 2 is a rechargeable electronic pipette from Sartorius with an
electronic brake and piston control system, exposed to software through
a JSON command interface. Over BLE it presents the Nordic UART Service.

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

### Models

Models are identified in software by `GET_MODEL` and set the valid
volume range. The development unit is the **LH-747081** (1-channel,
50–1,000 µL, model `SINGLE_CHANNEL_1000UL`, firmware `CP-7.0`).

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

## How the code works

The control logic lives in the `picus2` package (`src/picus2/`):

| Module | Responsibility |
| --- | --- |
| `client.py` | `Picus2Client`: scan + connect over BLE, number commands, await each response, and expose `get_version`, `aspirate`, `blow_out`, etc. |
| `protocol.py` | Pure helpers: build `{"no", "data"}` command bytes and parse `ACK` / `BEGIN` / data / `END` responses (no I/O). |
| `pipetting.py` | High-level techniques: `forward_pipette`, `reverse_pipette`, `multi_dispense`. |
| `constants.py` | Nordic UART UUIDs, scan defaults, speed limits, result tags. |

A command round-trip is: the client writes `{"no": N, "data": "CMD"}\r\n`
to the RX characteristic; the device notifies `ACK N`, `BEGIN N`,
optional data lines, a result tag (`OK`, `NOT_ALLOWED`, …), and `END N`.
Replies are matched by the command number `N`.

### Motor-control authorization

Motion commands are blocked until motor control is authorized on the
device. `Picus2Client.enable_motor_control()` sends
`ENABLE_MOTOR_CONTROL 1`, answers the on-screen prompt with the YES soft
key, then sets `AUTO 1` so buffered commands execute automatically.

> **Authorize with no tip mounted.** Answering YES with a tip on ejects
> it as a one-time reset. The pipette must also be in a pipetting mode,
> not the mode-selection menu.

## Connecting over Bluetooth

1. On the device, read the passkey under *Settings → Bluetooth →
   Bluetooth Passkey* (it rotates, so read it just before pairing).
2. Pair the pipette once through the **operating system** using that
   passkey. The firmware only answers commands over a bonded link, and
   programmatic pairing is unreliable, so OS-level pairing is the
   working path.
3. The pipette advertises a name like `Picus-46980628`. `bleak` reuses
   the OS bond on connect.

Nordic UART Service UUIDs:

| BLE item | UUID |
| --- | --- |
| Service | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` |
| RX (write) | `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` |
| TX (notify) | `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` |

```python
import asyncio
from picus2 import Picus2Client, forward_pipette

async def main():
    async with Picus2Client("Picus-46980628") as pipette:
        print(await pipette.get_model())          # SINGLE_CHANNEL_1000UL
        await pipette.enable_motor_control()       # authorize with NO tip
        await forward_pipette(pipette, 500, 7)     # aspirate + blow-out
        await pipette.disable_motor_control()

asyncio.run(main())
```

> **Bluetooth inside Docker** needs the container to share the host
> network namespace (`--network host`): otherwise `AF_BLUETOOTH` sockets
> fail with EAFNOSUPPORT even when the container is privileged and
> `/sys/class/bluetooth/hci0` is visible. If you cannot grant host
> networking, use the USB transport on `main` instead.

## Installation

```bash
python -m venv .venv
.venv/bin/pip install -e .          # needs Python >= 3.14
```

If the host Python is older, install the dependency and use the sources:

```bash
.venv/bin/pip install bleak
PYTHONPATH=src .venv/bin/python examples/example_forward.py
```

## Project layout

```
src/picus2/        BLE control library (client, protocol, pipetting)
tests/             unit tests (protocol, pipetting math)
examples/          example_forward.py (forward pipette over BLE)
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
