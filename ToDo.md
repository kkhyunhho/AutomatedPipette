# ToDo

> Cumulative task history for the AutomatedPipette project.
> Append new tasks below; never delete or rewrite past entries
> (see CLAUDE.md §4 Task Management).

## 2026-06-05 | Apply CommonClaude conventions to project root

### Background
The CommonClaude conventions repo is vendored under `CommonClaude/`.
Install its configuration at the project root so Claude Code picks it
up for the AutomatedPipette (Picus2 BLE pipette automation) project.

### Work items
- [x] Copy `CommonClaude/CLAUDE.md` to project root
- [x] Copy `CommonClaude/.claude/settings.json` to `.claude/`
- [x] Copy the 5 hook scripts to `.claude/hooks/`
- [x] Copy `CommonClaude/.clang-format` to project root
- [x] Create fresh `ToDo.md` for this project (this file)
- [x] Create fresh `LearnedPatterns.md` skeleton for this project
- [x] Leave `README.md` and `.gitignore` untouched (per user)

## 2026-06-05 | Commit CommonClaude install and PR to upstream

### Background
`coport-uni/AutomatedPipette` is a fork of the original
`kkhyunhho/AutomatedPipette` (fork main == upstream main, identical).
Commit the CommonClaude install, push to the fork, and open a PR
against the upstream original.

### Work items
- [ ] Cut branch `chore/apply-commonclaude-conventions` from `main`
- [ ] Stage explicit paths only (config files; not `CommonClaude/` or `docs/`)
- [ ] Commit with Conventional Commits format
- [ ] Push branch to fork (`origin` = coport-uni)
- [ ] Open PR: `coport-uni:chore/...` -> `kkhyunhho:main`

## 2026-06-05 | First wireless (BLE) smoke test of Picus 2

### Background
Verify the project can talk to the Picus 2 pipette wirelessly over BLE
using `bleak`, starting from the bundled example. Goal is a quick
`GET_VERSION` round-trip, not production control code.

### Work items
- [x] Install `bleak` BLE library
- [x] Scan for the pipette; found `Picus-46980628`
      (`FE:BE:2D:A2:35:1F`) via `claude_test/scan_ble.py`
- [x] Connect over BLE and send `GET_VERSION`
      via `claude_test/test_get_version.py`
- [x] Confirm wireless connect + write succeed without a PIN
- [x] Capture the `ACK / BEGIN / CP-7.0 / END` response
      (works only after bonding; this unit reports firmware CP-7.0)
- [x] Resolve Windows "add device" PIN prompt -- the passkey is shown
      on the device under `Settings -> Bluetooth -> Bluetooth Passkey`
      (`723904`); pair via Windows settings, then bleak reuses the bond
- [x] Conclusion: the pipette only answers commands over a bonded
      (passkey-paired) BLE link; programmatic WinRT pairing was
      unreliable, so OS-level pairing is the working path

## 2026-06-05 | Dry-run forward pipetting over BLE (empty tip, no liquid)

### Background
Exercise the motor (piston) commands end to end with no liquid, using an
empty tip, to validate the forward-pipetting sequence remotely. Research
came from the command reference and pipetting-basics PDFs.

### Key facts (from command reference)
- Command form: `{"no": 0, "data":"<CMD> <args>"}\r\n`.
- Motor commands require `ENABLE_MOTOR_CONTROL 1` first.
- Forward pipetting: `RUN_ASPIRATE <vol> <speed>` then
  `BLOW_OUT <go_home> <speed> <delay_ms>`; speed is 1..9.
- Results: `OK`, `NOT_ALLOWED`, `MISSING_PARAMETERS`, `FAILED`, etc.

### Work items
- [x] Read device model and safe volume range (read-only queries):
      SINGLE_CHANNEL_1000UL, min 50uL, nominal 1000uL
- [x] Discover why motor commands were NOT_ALLOWED: the device shows a
      "Motor control has been requested. Allow it?" prompt that must be
      answered YES (`TRIGGER_BUTTON_RIGHT`); pressing YES with a tip
      mounted also ejects the tip
- [x] Forward pipette dry-run (no tip): auto-press YES, then
      `RUN_ASPIRATE 200 7` -> OK, `BLOW_OUT 1 7 3000` -> OK
- [x] Disable motor control afterwards (`ENABLE_MOTOR_CONTROL 0`) -> OK
- [x] Conclusion: tip eject is a one-time reset only when a tip is
      mounted at authorization time; it is NOT required per pipetting
- [x] Found the final missing piece: send `AUTO 1` after authorization
      so buffered motor commands execute automatically (otherwise they
      wait for a TOP run trigger and return NOT_ALLOWED). Reference flow
      in `claude_test/forward_pipetting_v4.py` runs all `OK`.

## 2026-06-05 | Reverse pipetting over BLE (dry-run, no liquid)

### Background
Implement the reverse-pipetting technique remotely: aspirate target plus
excess, dispense only the target, then blow-out to discard the excess.
Reuses the proven flow (authorize -> AUTO 1 -> motor commands).

### Plan (1000uL model, dry-run)
- Target 500uL, excess 40uL, speed 4 (from pipetting-basics example).
- Sequence: `ENABLE_MOTOR_CONTROL 1` -> YES button -> `AUTO 1` ->
  `RUN_ASPIRATE 540 4` -> `RUN_DISPENSE 500 4` -> `BLOW_OUT 1 4 3000`
  -> `ENABLE_MOTOR_CONTROL 0`.

### Work items
- [x] Implement `claude_test/reverse_pipetting.py`
- [x] Run dry-run and confirm each step returns `OK`:
      ASPIRATE 540 -> DISPENSE 500 -> BLOW_OUT all OK
- [x] Record observed motion and responses

## 2026-06-05 | Forward pipetting with real liquid + multi-dispensing

### Background
First real-liquid run used the interactive forward script
(`forward_pipetting_liquid.py`, 500uL) and worked. Next, implement
multi-dispensing: aspirate the total plus excess once, then dispense
several equal aliquots, then blow-out the remainder.

### Plan (1000uL model)
- 3 x 100uL aliquots, pre-out 30uL, blow-out reserve 30uL
  -> aspirate 360uL (from pipetting-basics example), speed 4.
- Sequence: authorize -> AUTO 1 -> RUN_ASPIRATE 360 ->
  RUN_DISPENSE 30 (pre-out) -> RUN_DISPENSE 100 x3 -> BLOW_OUT.

### Work items
- [x] Forward pipetting with real liquid (500uL) confirmed working
- [x] Implement `claude_test/multi_dispensing.py` (dry-run validation)
- [x] Confirm each step returns `OK`: ASPIRATE 360 -> DISPENSE 30
      (pre-out) -> DISPENSE 100 x3 -> BLOW_OUT, all OK

## 2026-06-05 | Promote to production module `src/picus2/`

### Background
Consolidate the validated exploration into a reusable async package
(chosen design: package layout + async API). Production code, so follow
the full workflow: issue -> branch -> implement -> PR.

### Work items
- [x] Cut branch `feature/picus2-control-module` from `main`
- [x] Create GitHub issue (#3)
- [x] Add `pyproject.toml` (ruff line-length 80) and Python `.gitignore`
- [x] Implement `src/picus2/`: constants, protocol, client, pipetting
- [x] Add `tests/` unit tests (protocol + volume math); 12 pass
- [x] Add `examples/example_forward.py`
- [x] ruff check/format clean; hardware smoke test via the module OK
      (GET_VERSION CP-7.0, model SINGLE_CHANNEL_1000UL)
- [x] Commit (2), push branch, open PR (#4, closes #3)

## 2026-06-07 | Add USB serial transport via a transport abstraction

### Background
The module was BLE-only (`bleak`). USB serial now works in Docker
(issue #7) and is the preferred transport here. Refactor `Picus2Client`
to talk through a pluggable transport so the command protocol and the
pipetting helpers are shared by BLE and USB. The current BLE-only code
is preserved on the `bluetooth-connection` branch before refactoring.

### Design
- `errors.py`: shared exception hierarchy (avoids a client<->transport
  import cycle).
- `transport.py`: `Transport` ABC + `BleTransport` (bleak) +
  `SerialTransport` (pyserial; a reader thread frames `\r\n` lines and
  marshals them onto the event loop via `call_soon_threadsafe`).
- `Picus2Client(transport)` plus `over_ble(name)` / `over_serial(port)`
  factories. The protocol and pipetting helpers are unchanged.

### Work items
- [x] Create `bluetooth-connection` branch from the BLE-only code
- [x] Add `src/picus2/errors.py` and `src/picus2/transport.py`
      (`Transport` ABC + `BleTransport` + `SerialTransport`)
- [x] Refactor `client.py` to use a transport; add `over_ble` /
      `over_serial` factory methods (bump to 0.2.0)
- [x] Add serial constants and `pyserial` to `pyproject.toml`
- [x] Update `__init__` exports and the example; add `example_usb.py`
- [x] Add a hardware-free client/transport test (`FakeTransport`);
      14 unit tests pass
- [x] ruff clean, unit tests pass, USB hardware smoke test via the
      module OK: `over_serial("/dev/ttyACM0")` -> version CP-7.0,
      model SINGLE_CHANNEL_1000UL, nominal 1000uL, clean disconnect

## 2026-06-07 | Forward pipetting with real liquid over USB

### Background
First real-liquid actuation over the USB transport, using the module's
`Picus2Client.over_serial`. Reuses the proven flow (LP §3): authorize
motor control with NO tip mounted (the client also sends AUTO 1), then
aspirate -> move -> blow-out, with interactive pauses for the physical
steps. Run in a real terminal. Volume 500 uL, speed 7.

### Work items
- [x] Add `claude_test/forward_pipetting_usb.py` (interactive, over USB;
      ruff clean, compiles, module import OK)
- [ ] User runs it in a terminal with real liquid (500 uL, speed 7)
- [ ] Record the observed result

## 2026-06-07 | Write project READMEs from the Picus 2 manuals

### Background
The repo README was empty. Write a proper top-level README sourced from
the datasheet and command/pipetting references. Per the user, work
directly on `main` (no feature branch) and give each long-lived branch
a README matching its connection approach: `main` is USB-first /
universal control; `bluetooth-connection` is framed around BLE.

### Work items
- [x] Read the product datasheet for specs and model table (our unit is
      LH-747081, 1-ch 50-1,000 uL, model SINGLE_CHANNEL_1000UL, CP-7.0)
- [x] Write `README.md` on `main` (device specs, module architecture,
      USB/BLE connection, usage, safety)
- [x] Write `README.md` on the `bluetooth-connection` branch (BLE focus)

