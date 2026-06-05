# LearnedPatterns.md

> Patterns extracted from past work on the AutomatedPipette project.
> Consult the relevant sections before drafting new ToDo entries.
> Append new patterns after each task completes
> (see CLAUDE.md §9 Learned Patterns Reference).
>
> Last updated: 2026-06-05
> Total patterns: 6
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

## §99. Uncategorized

_None yet._
