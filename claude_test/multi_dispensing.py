# Debug: multi-dispensing dry-run over BLE (no liquid). Aspirate the total
# (pre-out + aliquots + blow-out reserve) once, dispense a pre-out aliquot
# (discarded), then several equal aliquots, then blow-out the remainder.
# Uses the proven flow: authorize motor control, set AUTO 1, run commands.
import asyncio
import json

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

ALIQUOT_VOLUME_UL = 100
NUM_ALIQUOTS = 3
EXCESS_VOLUME_UL = 30  # used for both the pre-out and the blow-out reserve
PIPETTE_SPEED = 4
BLOW_OUT_DELAY_MS = 3000
STEP_TIMEOUT_S = 25.0

ASPIRATE_TOTAL_UL = (
    EXCESS_VOLUME_UL + NUM_ALIQUOTS * ALIQUOT_VOLUME_UL + EXCESS_VOLUME_UL
)


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
        print("aspirate total:", ASPIRATE_TOTAL_UL, "uL")
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

        # Authorize motor control and enable automatic execution.
        await run_command(0, "ENABLE_MOTOR_CONTROL 1")
        await press("TRIGGER_BUTTON_RIGHT")
        await asyncio.sleep(3.0)
        await run_command(1, "AUTO 1")

        # Aspirate the full amount, then pre-out the first excess.
        await run_command(2, f"RUN_ASPIRATE {ASPIRATE_TOTAL_UL} {PIPETTE_SPEED}")
        await run_command(3, f"RUN_DISPENSE {EXCESS_VOLUME_UL} {PIPETTE_SPEED}")

        # Dispense the equal aliquots.
        no = 4
        for index in range(NUM_ALIQUOTS):
            print(f"-- aliquot {index + 1} of {NUM_ALIQUOTS} --")
            await run_command(no, f"RUN_DISPENSE {ALIQUOT_VOLUME_UL} {PIPETTE_SPEED}")
            no += 1

        # Blow out the remaining reserve and return home, then release.
        await run_command(no, f"BLOW_OUT 1 {PIPETTE_SPEED} {BLOW_OUT_DELAY_MS}")
        await run_command(no + 1, "ENABLE_MOTOR_CONTROL 0")
        print("sequence complete")


if __name__ == "__main__":
    asyncio.run(main())
