# Debug: full forward pipetting dry-run that auto-answers the motor-control
# authorization prompt (presses YES = TRIGGER_BUTTON_RIGHT). Pressing YES
# performs a tip eject, as the device warns. Empty tip, no liquid.
import asyncio
import json

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

ASPIRATE_VOLUME_UL = 1000
PIPETTE_SPEED = 5
STEP_TIMEOUT_S = 4.0


async def main():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found. Wake the pipette and retry.")
        return

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

        # Request motor control; the device shows the allow prompt.
        await run_command(0, "ENABLE_MOTOR_CONTROL 1")
        # Answer YES to authorize (this ejects the tip).
        await press("TRIGGER_BUTTON_RIGHT")
        await asyncio.sleep(3.0)
        # Now the motor commands should be allowed.
        await run_command(1, f"RUN_ASPIRATE {ASPIRATE_VOLUME_UL} {PIPETTE_SPEED}")
        await run_command(2, f"BLOW_OUT 1 {PIPETTE_SPEED} 3000")
        await run_command(3, "ENABLE_MOTOR_CONTROL 0")
        print("sequence complete")


if __name__ == "__main__":
    asyncio.run(main())
