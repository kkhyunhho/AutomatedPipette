"""Example: read model and version from the Picus 2 over USB serial.

Connect the pipette to the host with a USB cable, then run from the
project root:

    pip install -e .
    python examples/example_usb.py

USB needs no pairing. The pipette enumerates as a CDC-ACM port; adjust
``serial_port`` if it is not ``/dev/ttyACM0``.
"""

import asyncio
import logging

from picus2 import Picus2Client

serial_port = "/dev/ttyACM0"


async def main() -> None:
    """Open the serial link and print the model and firmware version."""
    async with Picus2Client.over_serial(serial_port) as pipette:
        print("model:", await pipette.get_model())
        print("version:", await pipette.get_version())
    print("done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
