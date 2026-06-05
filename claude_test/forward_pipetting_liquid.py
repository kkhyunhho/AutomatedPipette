# Debug: interactive forward pipetting with real liquid. Pauses for the
# physical steps (mount tip, dip in liquid, move to destination). Run this
# directly in a terminal so the Enter prompts work.
#
# Flow: authorize motor control with NO tip (so nothing ejects) -> AUTO 1
# -> mount tip + dip -> RUN_ASPIRATE -> move -> BLOW_OUT (dispense + home).
import asyncio
import json

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

VOLUME_UL = 500
PIPETTE_SPEED = 5
BLOW_OUT_DELAY_MS = 3000
STEP_TIMEOUT_S = 25.0


async def main():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found. Wake the pipette and retry.")
        return

    loop = asyncio.get_running_loop()
    state = {"done": asyncio.Event(), "no": -1, "result": None}

    def handle_rx(_, data: bytearray):
        text = bytes(data).decode("ascii", "replace").strip()
        print("   <<", text)
        parts = text.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            return
        tag, number = parts[0], int(parts[-1])
        if number != state["no"]:
            return
        if tag in ("OK", "NOT_ALLOWED", "FAILED", "SYNTAX_ERROR"):
            state["result"] = tag
        if tag == "END":
            state["done"].set()

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)

        async def run_command(no, command):
            state["no"] = no
            state["result"] = None
            state["done"].clear()
            payload = json.dumps({"no": no, "data": command}) + "\r\n"
            print(f">> [{no}] {command}")
            await client.write_gatt_char(
                UART_RX_CHAR_UUID, payload.encode(), response=False
            )
            try:
                await asyncio.wait_for(state["done"].wait(), timeout=STEP_TIMEOUT_S)
                print(f"   == [{no}] result: {state['result']}")
            except asyncio.TimeoutError:
                print(f"   == [{no}] TIMEOUT")

        async def press(button):
            payload = json.dumps({"button": button}) + "\r\n"
            print(f">> button {button}")
            await client.write_gatt_char(
                UART_RX_CHAR_UUID, payload.encode(), response=False
            )

        async def wait_enter(prompt):
            await loop.run_in_executor(None, input, prompt)

        await wait_enter(
            "STEP 1: Make sure NO tip is attached, then press Enter "
            "to authorize motor control..."
        )
        await run_command(0, "ENABLE_MOTOR_CONTROL 1")
        await press("TRIGGER_BUTTON_RIGHT")
        await asyncio.sleep(3.0)
        await run_command(1, "AUTO 1")

        await wait_enter(
            f"STEP 2: Attach a fresh tip and dip it into the liquid, "
            f"then press Enter to ASPIRATE {VOLUME_UL} uL..."
        )
        await run_command(2, f"RUN_ASPIRATE {VOLUME_UL} {PIPETTE_SPEED}")

        await wait_enter(
            "STEP 3: Lift the tip out and hold it over the destination, "
            "then press Enter to DISPENSE + blow-out..."
        )
        await run_command(3, f"BLOW_OUT 1 {PIPETTE_SPEED} {BLOW_OUT_DELAY_MS}")

        await wait_enter("STEP 4: Done. Press Enter to release motor control...")
        await run_command(4, "ENABLE_MOTOR_CONTROL 0")
        print("sequence complete")


if __name__ == "__main__":
    asyncio.run(main())
