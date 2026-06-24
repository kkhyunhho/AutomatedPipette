# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Conventions

For the big picture and all shared conventions — the "one cell, many
devices" architecture, code style, repo skeleton, codename naming, the
driver API contract, the (optional) FastAPI `/v1` server standard, the
hybrid integration model, testing strategy, and task/commit rules — see
**CommonClaude** (`kkhyunhho/CommonClaude`), the single source of truth.

This file holds only what is specific to **AutomatedPipette**: the
Sartorius Picus 2 electronic pipette, its BLE / USB transports, and the
device prerequisites. Where this file is silent, CommonClaude governs.

This project is a **device driver** for the codename **`picus2`**: package
[src/picus2/](src/picus2/), client class `Picus2Client` (async). It is a
library-only driver; no FastAPI `server/` is shipped (server is added per
need, not for every device — see CommonClaude).

## Environment

| Item    | Detail                                                      |
|---------|-------------------------------------------------------------|
| Runtime | Docker container (`--privileged`)                           |
| OS      | Ubuntu 24.04 (Noble)                                        |
| Python  | >= 3.12                                                     |

The pipette driver is **async** (`asyncio`); the blocking USB reader runs
on a background thread inside `SerialTransport`.

## Commands

All projects share one conda env, **`elec`** (electrochemistry-automation
lab; Python 3.12), where every driver package is `pip install -e`'d. New
terminals activate it automatically.

```bash
conda activate elec          # one-time per project: pip install -e ".[dev]"

ruff check src tests claude_test     # lint (80-col)
ruff format --check src tests claude_test
mypy                                  # types on src/picus2
pytest                                # unit tests
```

## Hardware / domain notes

**Device:** Sartorius Picus 2 electronic pipette. Two transports, hidden
behind a `Transport` abstraction (each imports its backend lazily):

- **BLE** — Nordic UART Service (`bleak`); the pipette is wireless and
  sleeps quickly, so scans retry.
- **USB serial** — CDC-ACM port (`pyserial`). Identify by USB identity
  **`24BC:2202`** (Sartorius VID `24BC`, Picus PID `2202`). The Entris-II
  balance shares the Sartorius VID (`24BC:0010`), so the pipette is matched
  by **full VID:PID**, never the vendor ID alone. `over_serial(port=None)`
  auto-detects it; an explicit path or `"VID:PID[:SERIAL]"` also works.

**Prerequisites / quirks:**

- The pipette must be in a **Pipetting mode**, not the mode-selection
  menu, or `ENABLE_MOTOR_CONTROL` returns `NOT_ALLOWED`.
- Enabling motor control ejects a mounted tip as a reset — do it over the
  trash.
- Motor control requires answering an on-device authorization prompt;
  the driver presses `TRIGGER_BUTTON_RIGHT` after `motor_prompt_delay`.
- The firmware parses one command per line, terminated by `\r\n`; result
  tags (`OK`, `SYNTAX_ERROR`, `NOT_ALLOWED`, …) frame each response.

Errors raise the `Picus2Error` hierarchy (`DeviceNotFoundError`,
`CommandTimeoutError`, `CommandError`).
