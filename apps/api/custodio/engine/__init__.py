"""Deterministic decision engine. Owned by lane L1.

Pure functions only: same inputs, same outputs. No I/O, no clock, no randomness, no model calls. The engine
never reads `InvoiceCase.expected` or `InvoiceCase.trap` (only `metrics` reads `expected`, to score a batch).
Semantics are ported from prototype/engine.js (`decideAll`, `audit`, `counterfactual`, `explain`) and specified in
docs/DESIGN.md §5.
"""

from __future__ import annotations

from custodio.engine.audit import audit
from custodio.engine.decide import decide_all

__all__ = ["audit", "decide_all"]
