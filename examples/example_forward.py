"""Example: forward pipette 500 uL over BLE.

Pair the pipette with the OS first, then run from the project root:

    pip install -e .
    python examples/example_forward.py

The pipette must be awake and in Pipetting mode. Authorization is done
with no tip mounted, so mount the tip after enabling motor control.
"""

import asyncio
import logging

from picus2 import Picus2Client, forward_pipette

device_name = "Picus-46980628"
transfer_volume_ul = 500
pipette_speed = 7


async def main() -> None:
    """Connect, run one forward-pipetting cycle, and release control."""
    async with Picus2Client(device_name) as pipette:
        print("model:", await pipette.get_model())
        print("version:", await pipette.get_version())
        await pipette.enable_motor_control()
        await forward_pipette(pipette, transfer_volume_ul, pipette_speed)
        await pipette.disable_motor_control()
    print("done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
