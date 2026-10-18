"""Pairs statement movements with the payments Blinka Keeper made. Pure: no I/O, no clock, no model.

Levels run in a fixed order over the whole statement, each payment taking the first free movement that fits:
1. exact: a reference (rail transfer id, invoice number, acta link) and the exact amount;
2. amount and date: the exact amount, within the date window, with the beneficiary named;
3. split: two to `max_split_parts` movements that add up exactly to the payment;
4. tolerance: a payment made in another currency, within the explicit FX tolerance.
What is left is a bank fee, a duplicate of another movement, or an outflow no paid invoice explains (red alert).
Movements and payments are visited in a canonical order, so the outcome does not depend on the input order, and a
movement is taken by one payment at most.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations

from custodio.contracts import DecisionStatus
from custodio.engine.formatting import counted, day_month, join_es, money, plus_minus_percent
from custodio.engine.text import fold, normalize_code, normalize_name
from custodio.reconciliation.models import (
    MatchLevel,
    MatchSettings,
    MovementResult,
    MovementStatus,
    PaidInvoice,
    PaymentResult,
    PaymentStatus,
    ReconciliationOutcome,
    StatementMovement,
    UnpaidInvoice,
)

CENT = Decimal("0.01")
HUNDRED = Decimal(100)
MIN_CODE_LENGTH = 4  # shorter invoice numbers («10») would turn up inside dates and amounts
MIN_NAME_LENGTH = 4
MIN_TAX_ID_LENGTH = 6
MAX_SPLIT_CANDIDATES = 12  # bounds the subsets tried for one payment
NEAR_MISS_EDITS = 2
_CODE_SEPARATORS = "-./#_"
_FEE = re.compile(
    r"\b(comision(es)?|commission|fees?|cuota de manejo|gmf|4 ?x ?1000|cargo bancario|gastos bancarios|"
    r"bank charges?|service charges?|iva comision)\b"
)
_UNPAID_STATE = {
    DecisionStatus.PENDING_APPROVAL: "esperaba aprobación",
    DecisionStatus.HOLD: "estaba retenida",
    DecisionStatus.REJECTED: "fue rechazada",
}


@dataclass(frozen=True)
class _Line:
    """A read outflow, ready to be matched."""

    movement: StatementMovement
    magnitude: Decimal
    currency: str | None
    text: str  # description and reference, as written


@dataclass(frozen=True)
class _Match:
    payment: PaidInvoice
    level: MatchLevel
    lines: tuple[_Line, ...]
    expected: Decimal
    reason: str

    @property
    def difference(self) -> Decimal | None:
        total = sum((line.magnitude for line in self.lines), Decimal(0))
        return None if total == self.expected else total - self.expected


Finder = Callable[[PaidInvoice, Sequence[_Line], MatchSettings], _Match | None]


def reconcile(
    movements: Sequence[StatementMovement],
    paid: Sequence[PaidInvoice],
    unpaid: Sequence[UnpaidInvoice],
    settings: MatchSettings,
) -> ReconciliationOutcome:
    ordered = sorted(movements, key=_content_key)
    payments = sorted(paid, key=lambda payment: payment.invoice_id)
    settled = {movement.id: result for movement in ordered if (result := _not_an_outflow(movement)) is not None}
    lines = [_line(movement) for movement in ordered if movement.id not in settled]
    matches = _match_all(payments, lines, settings)
    for match in matches.values():
        settled.update(_matched_results(match))
    leftovers = [line for line in lines if line.movement.id not in settled]
    settled.update({line.movement.id: _fee(line) for line in leftovers if _is_fee(line)})
    settled.update(_duplicates(lines, settled))
    settled.update(
        {line.movement.id: _unexplained(line, payments, unpaid) for line in lines if line.movement.id not in settled}
    )
    account_currency = _account_currency(movements, payments)
    return ReconciliationOutcome(
        movements=[settled[movement.id] for movement in movements],
        payments=[_payment_result(payment, matches.get(payment.invoice_id), account_currency) for payment in payments],
        settings=settings,
    )


# --- the levels -------------------------------------------------------------------------------------------------


def _match_all(payments: Sequence[PaidInvoice], lines: Sequence[_Line], settings: MatchSettings) -> dict[str, _Match]:
    matches: dict[str, _Match] = {}
    used: set[str] = set()
    for finder in (_exact, _amount_and_date, _split, _within_tolerance):
        for payment in payments:
            if payment.invoice_id in matches:
                continue
            free = [line for line in lines if line.movement.id not in used]
            match = finder(payment, free, settings)
            if match is not None:
                matches[payment.invoice_id] = match
                used.update(line.movement.id for line in match.lines)
    return matches


def _exact(payment: PaidInvoice, lines: Sequence[_Line], settings: MatchSettings) -> _Match | None:
    for line in lines:
        reference = _reference(payment, line)
        expected = _expected(payment, line.currency)
        if reference and expected == line.magnitude:
            reason = f"Referencia exacta a {reference} y el mismo monto: {money(expected, _currency(line))}."
            return _Match(payment, MatchLevel.EXACT, (line,), expected, reason)
    return None


def _amount_and_date(payment: PaidInvoice, lines: Sequence[_Line], settings: MatchSettings) -> _Match | None:
    for line in lines:
        expected = _expected(payment, line.currency)
        if expected == line.magnitude and _within_window(payment, line, settings) and _names_beneficiary(payment, line):
            reason = (
                f"Mismo monto ({money(expected, _currency(line))}), {_beneficiary(payment)} en la descripción y "
                f"{_timing(payment, line)}.{_near_miss(payment, line)}"
            )
            return _Match(payment, MatchLevel.AMOUNT_DATE, (line,), expected, reason)
    return None


def _split(payment: PaidInvoice, lines: Sequence[_Line], settings: MatchSettings) -> _Match | None:
    candidates = [line for line in lines if _related(payment, line, settings) and not _is_fee(line)]
    candidates = candidates[:MAX_SPLIT_CANDIDATES]
    for size in range(2, settings.max_split_parts + 1):
        for pieces in combinations(candidates, size):
            currencies = {line.currency for line in pieces}
            expected = _expected(payment, pieces[0].currency)
            if len(currencies) == 1 and expected is not None and sum(p.magnitude for p in pieces) == expected:
                currency = _currency(pieces[0])
                parts = " + ".join(money(piece.magnitude, currency) for piece in pieces)
                reason = (
                    f"Pago partido: {counted(size, 'movimiento', 'movimientos')} ({parts}) suman exactamente "
                    f"{money(expected, currency)} de {_invoice(payment)}."
                )
                return _Match(payment, MatchLevel.SPLIT, pieces, expected, reason)
    return None


def _within_tolerance(payment: PaidInvoice, lines: Sequence[_Line], settings: MatchSettings) -> _Match | None:
    fitting = [
        (abs(line.magnitude - expected), position, line, expected)
        for position, line in enumerate(lines)
        if line.currency != payment.currency
        and (expected := _expected(payment, line.currency)) is not None
        and _related(payment, line, settings)
        and abs(line.magnitude - expected) <= expected * settings.fx_tolerance_pct / HUNDRED
    ]
    if not fitting:
        return None
    _, _, line, expected = min(fitting, key=lambda item: (item[0], item[1]))
    currency = _currency(line)
    reason = (
        f"Pago en {payment.currency} convertido: el banco debitó {money(line.magnitude, currency)} y Blinka Keeper "
        f"calculó {money(expected, currency)}; la diferencia de {money(line.magnitude - expected, currency)} cabe "
        f"en la tolerancia de cambio de {plus_minus_percent(settings.fx_tolerance_pct)} ({_invoice(payment)})."
    )
    return _Match(payment, MatchLevel.TOLERANCE, (line,), expected, reason)


# --- what each movement and payment becomes ---------------------------------------------------------------------


def _matched_results(match: _Match) -> dict[str, MovementResult]:
    difference = match.difference
    status = MovementStatus.RECONCILED if difference is None else MovementStatus.RECONCILED_WITH_DIFFERENCE
    return {
        line.movement.id: MovementResult(
            movement_id=line.movement.id,
            status=status,
            level=match.level,
            invoice_id=match.payment.invoice_id,
            allocated=min(line.magnitude, match.expected),
            difference=difference,
            reason=match.reason,
        )
        for line in match.lines
    }


def _payment_result(payment: PaidInvoice, match: _Match | None, account_currency: str) -> PaymentResult:
    common = {
        "invoice_id": payment.invoice_id,
        "invoice_number": payment.invoice_number,
        "supplier_name": payment.supplier_name,
        "paid_on": payment.paid_on,
        "external_id": payment.external_id,
        "dashboard_url": payment.dashboard_url,
        "acta_url": payment.acta_url,
    }
    if match is None:
        expected = _expected(payment, account_currency)
        shown = money(expected, account_currency) if expected is not None else money(payment.amount, payment.currency)
        return PaymentResult(
            **common,
            expected=expected,
            currency=account_currency,
            status=PaymentStatus.PENDING,
            reason=f"Blinka Keeper pagó {shown} el {day_month(payment.paid_on)} y todavía no aparece en este extracto.",
        )
    return PaymentResult(
        **common,
        expected=match.expected,
        currency=_currency(match.lines[0]),
        status=PaymentStatus.CONFIRMED,
        level=match.level,
        movement_ids=[line.movement.id for line in match.lines],
        difference=match.difference,
        reason=match.reason,
    )


def _not_an_outflow(movement: StatementMovement) -> MovementResult | None:
    if not movement.read or movement.amount is None:
        reason = movement.unread_reason or "No se pudo leer este movimiento."
        return MovementResult(
            movement_id=movement.id,
            status=MovementStatus.UNREAD,
            reason=f"NO LEÍDO: {reason} Nadie lo interpretó; una persona debe revisarlo.",
        )
    if movement.amount >= 0:
        currency = movement.currency or ""
        reason = (
            f"Entrada de {money(movement.amount, currency)}: fuera de cuentas por pagar."
            if movement.amount > 0
            else "Movimiento sin monto: no salió dinero."
        )
        return MovementResult(movement_id=movement.id, status=MovementStatus.INFLOW, reason=reason)
    return None


def _fee(line: _Line) -> MovementResult:
    return MovementResult(
        movement_id=line.movement.id,
        status=MovementStatus.BANK_FEE,
        reason=f"Cargo del banco de {money(line.magnitude, _currency(line))}: comisión o impuesto, no un pago a un "
        "proveedor.",
    )


def _duplicates(lines: Sequence[_Line], settled: dict[str, MovementResult]) -> dict[str, MovementResult]:
    """A movement listed again: identical date, amount, currency, description and reference to another one."""
    groups: dict[tuple[object, ...], list[_Line]] = {}
    for line in lines:
        groups.setdefault(_twin_key(line.movement), []).append(line)
    found: dict[str, MovementResult] = {}
    for twins in groups.values():
        explained = [line for line in twins if line.movement.id in settled]
        anchor = (explained or twins)[0]
        for line in twins:
            if line is not anchor and line.movement.id not in settled:
                found[line.movement.id] = MovementResult(
                    movement_id=line.movement.id,
                    status=MovementStatus.DUPLICATE,
                    duplicate_of=anchor.movement.id,
                    reason=f"Igual al movimiento de la fila {anchor.movement.row} (misma fecha, monto y descripción): "
                    "el banco lo lista otra vez o lo cobró dos veces. Confírmalo con el banco.",
                )
    return found


def _unexplained(line: _Line, payments: Sequence[PaidInvoice], unpaid: Sequence[UnpaidInvoice]) -> MovementResult:
    currency = _currency(line)
    when = f" el {day_month(line.movement.booked_on)}" if line.movement.booked_on else ""
    base = f"Salió {money(line.magnitude, currency)}{when} y ninguna factura pagada por Blinka Keeper lo explica."
    return MovementResult(
        movement_id=line.movement.id,
        status=MovementStatus.UNMATCHED_OUTFLOW,
        reason=f"{base} {_hint(line, payments, unpaid)}",
    )


def _hint(line: _Line, payments: Sequence[PaidInvoice], unpaid: Sequence[UnpaidInvoice]) -> str:
    for invoice in unpaid:
        if _resembles_unpaid(invoice, line):
            state = _UNPAID_STATE.get(invoice.status, "no estaba autorizada")
            return (
                f"Coincide con {_invoice(invoice)}, que {state}: Blinka Keeper no la pagó. Revisa quién hizo este pago."
            )
    for payment in payments:
        reference = _reference(payment, line)
        expected = _expected(payment, line.currency)
        if reference and expected is not None:
            return (
                f"La referencia apunta a {_invoice(payment)}, pero Blinka Keeper pagó "
                f"{money(expected, _currency(line))}: el monto no coincide."
            )
    return "Revísalo: puede ser un pago hecho por fuera de Blinka Keeper."


# --- vocabulary -------------------------------------------------------------------------------------------------


def _content_key(movement: StatementMovement) -> tuple[object, ...]:
    return (
        movement.booked_on or date.min,
        movement.amount if movement.amount is not None else Decimal(0),
        movement.currency or "",
        movement.description,
        movement.reference or "",
        movement.quote,
        movement.read,
        movement.id,
    )


def _twin_key(movement: StatementMovement) -> tuple[object, ...]:
    return (movement.booked_on, movement.amount, movement.currency, fold(movement.description), movement.reference)


def _line(movement: StatementMovement) -> _Line:
    assert movement.amount is not None
    text = " ".join(part for part in (movement.description, movement.reference) if part)
    return _Line(movement=movement, magnitude=-movement.amount, currency=movement.currency, text=text)


def _currency(line: _Line) -> str:
    return line.currency or ""


def _account_currency(movements: Sequence[StatementMovement], payments: Sequence[PaidInvoice]) -> str:
    counts = Counter(movement.currency for movement in movements if movement.currency)
    if counts:
        return min(counts, key=lambda currency: (-counts[currency], currency))
    return payments[0].base_currency if payments else ""


def _expected(payment: PaidInvoice, currency: str | None) -> Decimal | None:
    """What the statement should show for `payment` in `currency`, or None when the two cannot be compared."""
    if currency == payment.currency:
        return payment.amount.quantize(CENT, rounding=ROUND_HALF_UP)
    if currency == payment.base_currency:
        return payment.amount_base.quantize(CENT, rounding=ROUND_HALF_UP)
    return None


def _reference(payment: PaidInvoice, line: _Line) -> str | None:
    """How the movement names `payment`, in words for the reason; None when it does not."""
    if payment.external_id and re.search(rf"(?<![\w]){re.escape(payment.external_id)}(?![\w])", line.text):
        return f"la transferencia {payment.external_id}"
    if payment.acta_url in line.text or f"/acta/{payment.invoice_id}" in line.text:
        return f"el acta de {payment.invoice_id}"
    if payment.invoice_number and _names_code(payment.invoice_number, line.text):
        return f"la factura {payment.invoice_number}"
    return None


def _names_code(code: str, text: str) -> bool:
    """Whether `text` carries `code` whole: «AC-2026-10» is not inside «AC-2026-10-S»."""
    characters = [char for char in normalize_code(code)]
    if len(characters) < MIN_CODE_LENGTH:
        return False
    pattern = r"[\s\-./#_]*".join(map(re.escape, characters))
    upper = fold(text).upper()
    for match in re.finditer(pattern, upper):
        before = upper[: match.start()].rstrip(_CODE_SEPARATORS)
        after = upper[match.end() :].lstrip(_CODE_SEPARATORS)
        if not (before and before[-1].isalnum()) and not (after and after[0].isalnum()):
            return True
    return False


def _names_beneficiary(payment: PaidInvoice | UnpaidInvoice, line: _Line) -> bool:
    squeezed = re.sub(r"[^a-z0-9]", "", fold(line.text))
    names = {normalize_name(name) for name in payment.names}
    if any(len(name) >= MIN_NAME_LENGTH and name in squeezed for name in names):
        return True
    tax_id = normalize_code(payment.tax_id or "") if isinstance(payment, PaidInvoice) else ""
    return len(tax_id) >= MIN_TAX_ID_LENGTH and tax_id in normalize_code(line.text)


def _within_window(payment: PaidInvoice, line: _Line, settings: MatchSettings) -> bool:
    booked = line.movement.booked_on
    return booked is not None and abs((booked - payment.paid_on).days) <= settings.date_window_days


def _related(payment: PaidInvoice, line: _Line, settings: MatchSettings) -> bool:
    return _reference(payment, line) is not None or (
        _within_window(payment, line, settings) and _names_beneficiary(payment, line)
    )


def _resembles_unpaid(invoice: UnpaidInvoice, line: _Line) -> bool:
    if invoice.invoice_number and _names_code(invoice.invoice_number, line.text):
        return True
    amounts = {
        invoice.amount.quantize(CENT, rounding=ROUND_HALF_UP) if line.currency == invoice.currency else None,
        invoice.amount_base.quantize(CENT, rounding=ROUND_HALF_UP) if line.currency == invoice.base_currency else None,
    }
    return line.magnitude in amounts and _names_beneficiary(invoice, line)


def _is_fee(line: _Line) -> bool:
    return _FEE.search(fold(line.text)) is not None


def _timing(payment: PaidInvoice, line: _Line) -> str:
    assert line.movement.booked_on is not None
    days = (line.movement.booked_on - payment.paid_on).days
    paid = f"del pago del {day_month(payment.paid_on)}"
    if days == 0:
        return f"el mismo día {paid}"
    return f"{counted(abs(days), 'día', 'días')} {'después' if days > 0 else 'antes'} {paid}"


def _near_miss(payment: PaidInvoice, line: _Line) -> str:
    """Names a reference that looks like the invoice number but is not it (a typo the bank or a person made)."""
    if not payment.invoice_number:
        return ""
    wanted = normalize_code(payment.invoice_number)
    close = [
        written for written, code in _tokens(line.text) if code != wanted and _edits(code, wanted) <= NEAR_MISS_EDITS
    ]
    if not close:
        return ""
    written = join_es([f"«{token}»" for token in close])
    return f" La referencia {written} se parece a {payment.invoice_number} pero no es igual; se emparejó sin ella."


def _tokens(text: str) -> Iterable[tuple[str, str]]:
    """Each code-like word of `text`, as written and normalized."""
    for raw in text.split():
        code = normalize_code(raw)
        if len(code) >= MIN_CODE_LENGTH and any(char.isdigit() for char in code):
            yield raw.strip(_CODE_SEPARATORS + ",;:()"), code


def _edits(first: str, second: str) -> int:
    """Optimal string alignment distance: insertions, deletions, substitutions and adjacent swaps."""
    rows = [list(range(len(second) + 1))]
    for i, a in enumerate(first, start=1):
        row = [i]
        for j, b in enumerate(second, start=1):
            cost = 0 if a == b else 1
            row.append(min(rows[-1][j] + 1, row[j - 1] + 1, rows[-1][j - 1] + cost))
            if i > 1 and j > 1 and a == second[j - 2] and first[i - 2] == b:
                row[j] = min(row[j], rows[-2][j - 2] + 1)
        rows.append(row)
    return rows[-1][-1]


def _beneficiary(payment: PaidInvoice) -> str:
    return payment.supplier_name or (payment.names[0] if payment.names else "el beneficiario")


def _invoice(invoice: PaidInvoice | UnpaidInvoice) -> str:
    number = f"la factura {invoice.invoice_number}" if invoice.invoice_number else "la factura"
    return f"{number} ({invoice.invoice_id})"
