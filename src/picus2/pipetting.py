"""High-level pipetting modes built on :class:`Picus2Client`.

Each mode assumes motor control is already enabled on the client (see
:meth:`picus2.client.Picus2Client.enable_motor_control`).
"""

from __future__ import annotations

from . import constants
from .client import Picus2Client

# Default excess volumes (microliters) for the techniques that need them.
default_reverse_excess_ul = 40
default_multi_excess_ul = 30


def multi_dispense_total(aliquot_ul: int, count: int, excess_ul: int) -> int:
    """Compute the aspiration volume for a multi-dispense run.

    The total covers a pre-out aliquot, every dispensed aliquot, and a
    blow-out reserve (the pre-out and reserve each use ``excess_ul``).

    Args:
        aliquot_ul: Volume of each dispensed aliquot.
        count: Number of aliquots to dispense.
        excess_ul: Excess used for both the pre-out and the reserve.

    Returns:
        Total volume to aspirate, in microliters.
    """
    return excess_ul + count * aliquot_ul + excess_ul


async def forward_pipette(
    client: Picus2Client,
    volume_ul: int,
    speed: int,
    *,
    delay_ms: int = constants.default_blow_out_delay_ms,
) -> None:
    """Run a forward-pipetting cycle.

    Aspirates the target volume, then dispenses it with a blow-out. This
    is the default, factory-calibrated technique.

    Args:
        client: A connected, motor-enabled client.
        volume_ul: Volume to transfer, in microliters.
        speed: Motor speed (1..9).
        delay_ms: Blow-out delay before the go-home move.
    """
    await client.aspirate(volume_ul, speed)
    await client.blow_out(speed=speed, delay_ms=delay_ms)


async def reverse_pipette(
    client: Picus2Client,
    target_ul: int,
    speed: int,
    *,
    excess_ul: int = default_reverse_excess_ul,
    delay_ms: int = constants.default_blow_out_delay_ms,
) -> None:
    """Run a reverse-pipetting cycle.

    Aspirates the target plus an excess, dispenses only the target, then
    blows out the excess. Suited to viscous, foaming, or small volumes.

    Args:
        client: A connected, motor-enabled client.
        target_ul: Volume to deliver, in microliters.
        speed: Motor speed (1..9).
        excess_ul: Extra volume aspirated and later discarded.
        delay_ms: Blow-out delay before the go-home move.
    """
    await client.aspirate(target_ul + excess_ul, speed)
    await client.dispense(target_ul, speed)
    await client.blow_out(speed=speed, delay_ms=delay_ms)


async def multi_dispense(
    client: Picus2Client,
    aliquot_ul: int,
    count: int,
    speed: int,
    *,
    excess_ul: int = default_multi_excess_ul,
    delay_ms: int = constants.default_blow_out_delay_ms,
) -> None:
    """Run a multi-dispense cycle.

    Aspirates the total once, dispenses a pre-out aliquot (discarded for
    first-aliquot accuracy), dispenses ``count`` equal aliquots, then
    blows out the reserve.

    Args:
        client: A connected, motor-enabled client.
        aliquot_ul: Volume of each dispensed aliquot.
        count: Number of aliquots to dispense.
        speed: Motor speed (1..9).
        excess_ul: Excess used for the pre-out and the reserve.
        delay_ms: Blow-out delay before the go-home move.

    Raises:
        ValueError: If ``count`` is not positive.
    """
    if count <= 0:
        raise ValueError("count must be positive")
    total = multi_dispense_total(aliquot_ul, count, excess_ul)
    await client.aspirate(total, speed)
    await client.dispense(excess_ul, speed)
    for _ in range(count):
        await client.dispense(aliquot_ul, speed)
    await client.blow_out(speed=speed, delay_ms=delay_ms)
