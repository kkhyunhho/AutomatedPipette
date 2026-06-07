# LearnedPatterns.md

> Patterns extracted from past work on the AutomatedPipette project.
> Consult the relevant sections before drafting new ToDo entries.
> Append new patterns after each task completes
> (see CLAUDE.md §9 Learned Patterns Reference).
>
> Last updated: 2026-06-07
> Total patterns: 7
>
> Provenance format: `(from ToDo#N)` where N is the 1-based index of the
> top-level `##` section in `ToDo.md` at the time of extraction.

---

## §1. Recurring Issues

_None yet._

## §2. Solved Gotchas

_None yet._

## §3. Library Quirks

- Picus 2 ignores BLE commands until the link is bonded.
  - **Problem**: Connect, notify, and write all succeed over the Nordic
    UART Service, but the pipette never sends a response.
  - **Cause**: The firmware only answers commands over a bonded
    (passkey-paired) link; an unbonded connection is silently ignored.
  - **Fix**: Pair with the device passkey once, then reconnect; bleak
    reuses the existing OS bond.
  - **Rule**: Always bond the Picus 2 before expecting command replies.
  - (from ToDo#3)

- Picus 2 commands need a `\r\n` terminator.
  - **Problem**: `{"data":"GET_VERSION"}` sent with no line ending got no
    reply even after bonding.
  - **Cause**: The device parses commands line by line and waits for the
    terminator before acting.
  - **Fix**: Append `\r\n` to every command string before writing.
  - **Rule**: Always terminate Picus 2 BLE/USB commands with `\r\n`.
  - (from ToDo#3)

- WinRT `winrt` projection splits overloads into suffixed methods.
  - **Problem**: `DevicePairingRequestedEventArgs.accept(pin)` and the
    two-argument `pair_async(...)` both raise `Invalid parameter count`.
  - **Cause**: The Python `winrt` projection exposes each overload under
    a distinct name instead of one variadic method.
  - **Fix**: Use `accept_with_pin(pin)` and
    `pair_with_protection_level_async(...)`; inspect with
    `dir(obj)` to find the right suffix.
  - **Rule**: Never assume a single overloaded WinRT method; look for
    `*_with_*` variants when arg counts are rejected.
  - (from ToDo#3)

- Picus 2 motor commands need on-device authorization first.
  - **Problem**: `RUN_INIT`/`RUN_ASPIRATE`/`BLOW_OUT` return
    `NOT_ALLOWED` even after `ENABLE_MOTOR_CONTROL 1`.
  - **Cause**: `ENABLE_MOTOR_CONTROL 1` raises an on-screen prompt
    ("Motor control has been requested. Allow it?") that must be
    answered before motor commands run; the pipette must also be in a
    pipetting mode, not the mode-selection menu.
  - **Fix**: After `ENABLE_MOTOR_CONTROL 1`, send the YES soft key
    `{"button":"TRIGGER_BUTTON_RIGHT"}`. Pressing YES ejects a mounted
    tip (a one-time reset); authorize with no tip to avoid ejection.
    `SCREENSHOT <fmt>` returns a Base64 image to inspect such prompts.
  - **Rule**: Always answer the motor-control prompt (button YES) and be
    in pipetting mode before sending motor commands.
  - (from ToDo#4)

- Buffered motor commands need AUTO 1 to execute remotely.
  - **Problem**: After authorizing motor control, `RUN_ASPIRATE`/
    `BLOW_OUT` still hang (no END) and end up `NOT_ALLOWED`; they only
    run if the physical TOP/run button is pressed (seen as incoming
    `{"button":"TOP_PRESSED"}` events).
  - **Cause**: Motor commands are buffered and default to manual
    execution, waiting for a run trigger.
  - **Fix**: Send `AUTO 1` once after authorization so queued motor
    commands execute automatically; then aspirate/blow-out return `OK`
    immediately. (Alternative: emulate `TRIGGER_BUTTON_TOP` per command.)
  - **Rule**: Always set `AUTO 1` for fully remote motor sequences.
  - (from ToDo#4)

- pyserial is blocking; bridge it to asyncio with a reader thread.
  - **Problem**: The async `Picus2Client` needs serial reads delivered
    like BLE notifications, but `pyserial` has no asyncio API and its
    `read()` blocks.
  - **Cause**: `serial.Serial` is a synchronous, thread-oriented API.
  - **Fix**: Run a daemon reader thread that frames `\r\n` lines and
    hands each to the event loop via `loop.call_soon_threadsafe`, so the
    client's line handler always runs on the loop thread (as for BLE).
    Use a short `timeout` so the loop can poll a stop flag for shutdown,
    and wrap blocking `write()` in `run_in_executor`.
  - **Rule**: Never call blocking pyserial APIs from the event loop;
    isolate them in a thread and marshal results back with
    `call_soon_threadsafe`.
  - (from ToDo#9)

## §4. Workflow Lessons

_None yet._

## §5. Environment Specifics

- Programmatic BLE pairing on Windows is unreliable; pair via Settings.
  - **Problem**: WinRT custom pairing with the correct passkey returns
    status 19 (Failed), even though the handler accepts the PIN.
  - **Cause**: The Windows BLE pairing ceremony is fragile from code
    (lingering GATT sessions, ceremony quirks).
  - **Fix**: Pair once through Settings -> Bluetooth -> Add device using
    the passkey from the device menu (`Settings -> Bluetooth ->
    Bluetooth Passkey`), then let bleak reuse the bond.
  - **Rule**: On Windows, prefer OS Settings pairing over programmatic
    WinRT pairing for BLE devices.
  - (from ToDo#3)

- USB serial is the reliable Picus 2 transport inside Docker.
  - **Problem**: BLE from a container needs the host network namespace
    (`--network host`); without it `AF_BLUETOOTH` sockets fail with
    EAFNOSUPPORT even when privileged and `hci0` is visible.
  - **Cause**: Bluetooth sockets are netns-scoped; serial devices are
    not -- a `/dev/ttyACM*` node is reachable in a privileged container
    with no special networking.
  - **Fix**: Drive the pipette over USB. It enumerates as a CDC-ACM
    device (`/dev/ttyACM0`, `24bc:2202`, serial `46980628`); send the
    same JSON commands at 9600 8N1. No bonding/pairing is required.
  - **Rule**: Prefer USB serial over BLE for the Picus 2 in Docker;
    reserve BLE for hosts you can launch with `--network host`.
  - (from ToDo#8)

## §99. Uncategorized

_None yet._
