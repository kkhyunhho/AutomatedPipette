# Debug: forward pipetting dry-run while the pipette is in Pipetting mode.
# Waits for each command's END before the next. Empty tip, no liquid.
# RUN_INIT is omitted because entering Pipetting mode already homes.
import asyncio

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

ASPIRATE_VOLUME_UL = 500
PIPETTE_SPEED = 5
BLOW_OUT_GO_HOME = 1
BLOW_OUT_DELAY_MS = 3000
STEP_TIMEOUT_S = 25.0

SEQUENCE = [
    "ENABLE_MOTOR_CONTROL 1",
    f"RUN_ASPIRATE {ASPIRATE_VOLUME_UL} {PIPETTE_SPEED}",
    f"BLOW_OUT {BLOW_OUT_GO_HOME} {PIPETTE_SPEED} {BLOW_OUT_DELAY_MS}",
    "ENABLE_MOTOR_CONTROL 0",
]


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
        for index, command in enumerate(SEQUENCE):
            state["no"] = index
            state["result"] = None
            state["done"].clear()
            payload = '{"no": ' + str(index) + ', "data":"' + command + '"}\r\n'
            print(f">> [{index}] {command}")
            await client.write_gatt_char(
                UART_RX_CHAR_UUID, payload.encode(), response=False
            )
            try:
                await asyncio.wait_for(state["done"].wait(), timeout=STEP_TIMEOUT_S)
                print(f"   == [{index}] result: {state['result']}")
            except asyncio.TimeoutError:
                print(f"   == [{index}] TIMEOUT (no END received)")
        print("sequence complete")


if __name__ == "__main__":
    asyncio.run(main())
