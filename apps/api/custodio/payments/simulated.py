from __future__ import annotations

from dataclasses import dataclass

from custodio.payments.port import SIMULATED, Clock, PaymentOrder, PaymentReceipt


@dataclass(frozen=True)
class SimulatedRail:
    """Moves no money and touches no network; the receipt says so."""

    clock: Clock
    name: str = SIMULATED

    def execute(self, order: PaymentOrder) -> PaymentReceipt:
        return PaymentReceipt(rail=SIMULATED, status="simulated", executed_at=self.clock())
