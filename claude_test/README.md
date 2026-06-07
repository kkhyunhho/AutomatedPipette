# claude_test Index

Debug, exploratory, and throwaway scripts live here (see CLAUDE.md §3).
Each row records what a file does and what was learned.

| File | Purpose | Findings |
|------|---------|----------|
| `scan_ble.py` | Scan nearby BLE devices and flag any named `Picus-*`. | Found the pipette as `Picus-46980628` (address `FE:BE:2D:A2:35:1F`). |
| `test_get_version.py` | Connect to the Picus 2 over BLE and send `GET_VERSION` once, printing notifications. | BLE connect/send succeeds with no PIN. No response captured yet; pairing/notify behavior still under investigation. The official guide expects `ACK / BEGIN / CP-3.8 / END`. |
| `diagnose_ble.py` | Dump the full GATT table, enable notify, send `GET_VERSION`, wait. | GATT is correct: NUS service with RX (write/write-no-response) and TX (notify), plus Nordic Secure DFU. Connect/notify/write all succeed but no notification arrives. |
| `test_write_response.py` | Send `GET_VERSION` with `response=True` to detect an encryption/auth requirement. | Write-with-response is ACCEPTED, so the ATT layer does not require encryption. Device still sends no response. |
| `test_pair_then_send.py` | Call `client.pair()` (bond) before sending. | Pairing FAILS (`Could not pair: FAILED`) and breaks notify. Device likely needs a PIN we do not have, or a device-side mode must be enabled. |
| `inspect_accept.py` | Inspect the WinRT `DevicePairingRequestedEventArgs` to find how to supply a PIN. | The PIN-providing overload is exposed as `accept_with_pin(pin)`, not `accept(pin)`. Device requests pairing kind 4 (ProvidePin). |
| `pair_with_passkey.py` | Pair using the device passkey (`723904`) via WinRT custom pairing, then send `GET_VERSION`. | Handler now accepts the PIN, but `pair_async` returns status 19 (Failed). Programmatic pairing unreliable; OS Settings pairing is the fallback. |
| `query_info.py` | Send read-only queries (model, volumes, battery) over the bonded link. | Unit is `SINGLE_CHANNEL_1000UL`, firmware CP-7.0, nominal 1000uL, min 50uL, battery 93%. Responses echo the sent `no` value. |
| `forward_pipetting_dryrun.py` | Forward pipetting dry-run with fixed waits between motor commands. | Motor commands were cut off: disabling motor control too early left `RUN_ASPIRATE`/`BLOW_OUT` as `NOT_ALLOWED`. |
| `forward_pipetting_v2.py` | Same sequence but waits for each command's `END` before the next. | Motor commands BEGIN but never END while on the mode-selection menu; they resolve to `NOT_ALLOWED`. Root cause: pipette not in Pipetting mode. |
| `forward_pipetting_v3.py` | Aspirate + blow-out only (no `RUN_INIT`), to run while the pipette is in Pipetting mode. | Still `NOT_ALLOWED`: a tip-ejection confirmation dialog blocks motor commands at the start of the flow. |
| `capture_screenshot.py` | Capture the pipette screen via `SCREENSHOT <fmt>`, decode the Base64 payload between BEGIN/END, save an image. | Works: 160x270 BMP. Confirmed the Pipetting screen (1000uL, soft keys MENU/EDIT/ADV). |
| `capture_prompt.py` | Send `RUN_ASPIRATE`, then screenshot to capture the prompt and its soft-key answers. | Revealed the prompt: "Motor control has been requested. Do you want to allow it? WARNING: By pressing YES a tip eject will be performed." Soft keys NO (left) / YES (right). |
| `forward_pipetting_auto.py` | Full forward pipetting that auto-answers the motor-control prompt by pressing YES (`TRIGGER_BUTTON_RIGHT`), then aspirate + blow-out. | YES authorizes motor control (ejects a tip only if one is mounted). Aspirate/blow-out still `NOT_ALLOWED` without AUTO 1 (commands wait for a run trigger). |
| `forward_pipetting_v4.py` | Adds `AUTO 1` after authorization so buffered motor commands auto-execute. | WORKS end to end: ENABLE -> YES -> AUTO 1 -> RUN_ASPIRATE -> BLOW_OUT -> disable, all `OK`. This is the reference forward-pipetting flow. |
| `reverse_pipetting.py` | Reverse pipetting: aspirate target+excess, dispense only target, blow-out the excess (authorize -> AUTO 1 -> motor commands). | WORKS: ASPIRATE 540 -> DISPENSE 500 -> BLOW_OUT 1 4 3000, all `OK`. Volumes/speed are top-of-file constants. |
| `forward_pipetting_liquid.py` | Interactive forward pipetting with real liquid; pauses (Enter) for mount-tip / dip / move steps. Run in a terminal. | WORKS with 500uL water: authorize (no tip) -> AUTO 1 -> mount+dip -> aspirate -> move -> blow-out. |
| `multi_dispensing.py` | Multi-dispensing: aspirate the total once, pre-out, then N equal aliquots, then blow-out (authorize -> AUTO 1 -> motor commands). | WORKS (dry-run): ASPIRATE 360 -> DISPENSE 30 -> DISPENSE 100 x3 -> BLOW_OUT, all `OK`. Aliquot/count/excess are top-of-file constants. |
| `usb_get_version.py` | Send `GET_VERSION` to the Picus 2 over USB serial (`/dev/ttyACM0`, 9600 8N1) and read the reply. | WORKS: `ACK 0 / BEGIN 0 / CP-7.0 / END 0`. Same JSON protocol as BLE, but no bonding needed and no Docker `--network host` requirement. The pipette enumerates as `24bc:2202` serial `46980628`. |
