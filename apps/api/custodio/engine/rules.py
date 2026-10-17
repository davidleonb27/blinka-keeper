"""The twelve rules. Each one reads a RuleContext and returns its result with a Spanish reason and concrete numbers.

A rule never decides the verdict alone and never pays; it only says pass, hold, escalate or skipped, and, when it
fails, the change that would have made it pass (used by the counterfactual).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from custodio.contracts import (
    RULES,
    AgreementKind,
    Beneficiary,
    ExtractedField,
    ExtractedInvoice,
    Policy,
    RuleOutcome,
    RuleResult,
)
from custodio.engine.beneficiaries import BeneficiaryMatch
from custodio.engine.facts import Charge, InvoiceFacts
from custodio.engine.formatting import (
    clip,
    counted,
    day_month,
    join_es,
    money,
    money_with_base,
    month_name,
    percent,
    plus_minus_percent,
    signed_percent,
)
from custodio.engine.injection import find_instruction
from custodio.engine.text import normalize_code
from custodio.engine.units import same_month

DUPLICATE_AMOUNT_TOLERANCE = Decimal("0.005")  # R5: "the same amount" means within ±0.5 %
HUNDRED = Decimal(100)
KEY_FIELDS = (("supplier_name", "proveedor"), ("amount", "monto"), ("currency", "moneda"), ("account_number", "cuenta"))
IDENTITY_FIELDS = (("supplier_tax_id", "identificación fiscal"),)  # optional, but trusted only when verified
TEXT_FIELDS = (
    "supplier_name",
    "supplier_tax_id",
    "invoice_number",
    "issue_date",
    "due_date",
    "amount",
    "currency",
    "bank_name",
    "account_number",
    "description",
)
# A dollar sign names a currency only next to the ISO code that was read or that code's national prefix.
DOLLAR_PREFIXES = {"US": "USD", "R": "BRL", "MX": "MXN", "COL": "COP", "CLP": "CLP"}
DOLLAR_PREFIX = re.compile(r"(?<![A-Z])(US|R|MX|COL|CLP)\$")

_SPECS = {spec.id: spec for spec in RULES}


@dataclass(frozen=True)
class RuleContext:
    invoice: InvoiceFacts
    extraction: ExtractedInvoice
    policy: Policy
    fx: Mapping[str, Decimal]
    match: BeneficiaryMatch
    earlier: tuple[Charge, ...]  # this supplier's charges before this invoice: history and earlier in the batch
    nearby: tuple[Charge, ...]  # this supplier's charges inside the split window, this invoice included
    spent_auto: Decimal  # what the agent paid alone in the invoice's month, before it
    balance: Decimal  # available balance before this invoice

    @property
    def supplier(self) -> str:
        if self.match.beneficiary:
            return self.match.beneficiary.name
        return self.invoice.supplier_name or "el proveedor"


@dataclass(frozen=True)
class RuleCheck:
    result: RuleResult
    fix: str | None  # what would have made the rule pass, phrased to follow "Se habría pagado sola si …"


def check(rule_id: str, outcome: RuleOutcome, reason: str, *, fix: str | None = None, **facts: object) -> RuleCheck:
    spec = _SPECS[rule_id]
    result = RuleResult(rule_id=spec.id, key=spec.key, label=spec.label, outcome=outcome, reason=reason, facts=facts)
    return RuleCheck(result=result, fix=fix)


# R1 · Lectura confiable -----------------------------------------------------------------------------------------


def reading(ctx: RuleContext) -> RuleCheck:
    minimum = ctx.policy.min_confidence
    currency_quote = _ambiguous_currency_quote(ctx.extraction.currency)
    problems = [
        problem
        for name, label in KEY_FIELDS
        if not (name == "currency" and currency_quote)
        if (problem := _field_problem(ctx, name, label))
    ]
    problems += [
        problem
        for name, label in IDENTITY_FIELDS
        if getattr(ctx.extraction, name).value is not None
        if (problem := _field_problem(ctx, name, label))
    ]
    if currency_quote is not None:
        confidence = percent(_confidence(ctx.extraction.currency))
        reason = (
            f"La moneda no es clara: «{currency_quote}» puede ser pesos o dólares; se leyó "
            f"{ctx.extraction.currency.value} con confianza de {confidence}."
        )
        if problems:
            reason += f" Además, no se leyó con confianza: {join_es(problems)}."
        return check("R1", RuleOutcome.ESCALATE, reason, fix="una persona confirmara la moneda")
    if problems:
        return check(
            "R1",
            RuleOutcome.ESCALATE,
            f"No se leyó con confianza: {join_es(problems)}.",
            fix="una persona confirmara los datos o llegara un documento legible",
        )
    lowest = min(_confidence(getattr(ctx.extraction, name)) for name, _ in KEY_FIELDS)
    return check(
        "R1",
        RuleOutcome.PASS,
        f"Proveedor, monto, moneda y cuenta se leyeron con cita verificada y confianza de {percent(minimum)} o más "
        f"(la menor fue {percent(lowest)}).",
    )


def _field_problem(ctx: RuleContext, name: str, label: str) -> str | None:
    field: ExtractedField = getattr(ctx.extraction, name)
    if field.value is None:
        return f"{label} (no se leyó)"
    if not field.verified:
        return f"{label} (sin cita verificada en el documento)"
    if _confidence(field) < ctx.policy.min_confidence:
        return f"{label} (confianza de {percent(_confidence(field))}, mínima {percent(ctx.policy.min_confidence)})"
    if name == "amount" and ctx.invoice.amount is None:
        return f"{label} («{field.value}» no es un monto válido)"
    return None


def _confidence(field: ExtractedField) -> Decimal:
    return Decimal(str(field.confidence))


def _ambiguous_currency_quote(field: ExtractedField) -> str | None:
    quote = field.evidence.quote if field.evidence else None
    if field.value is None or quote is None or "$" not in quote or _names_currency(quote.upper(), field.value):
        return None
    return clip(quote)


def _names_currency(quote: str, code: str) -> bool:
    wanted = code.strip().upper()
    if re.search(rf"(?<![A-Z]){re.escape(wanted)}(?![A-Z])", quote):
        return True
    return any(DOLLAR_PREFIXES[prefix] == wanted for prefix in DOLLAR_PREFIX.findall(quote))


# R2 · Sin instrucciones escondidas ------------------------------------------------------------------------------


def instructions(ctx: RuleContext) -> RuleCheck:
    hidden = ctx.extraction.hidden_findings
    fix = "el documento no trajera texto dirigido al agente"
    if hidden:
        first = hidden[0]
        return check(
            "R2",
            RuleOutcome.ESCALATE,
            f"El documento trae {counted(len(hidden), 'texto oculto', 'textos ocultos')} ({first.detail.rstrip('.')}): "
            f"«{clip(first.text)}». El agente no obedece texto de las facturas.",
            fix=fix,
            hidden_count=len(hidden),
        )
    found = find_instruction(_document_text(ctx.extraction))
    if found:
        return check(
            "R2",
            RuleOutcome.ESCALATE,
            f"El documento trae instrucciones dirigidas al agente en la línea {found.number}: «{clip(found.text)}». "
            "El agente no obedece texto de las facturas.",
            fix=fix,
            line=found.number,
        )
    return check("R2", RuleOutcome.PASS, "El documento no trae texto oculto ni instrucciones dirigidas al agente.")


def _document_text(extraction: ExtractedInvoice) -> str:
    values = (getattr(extraction, name).value for name in TEXT_FIELDS)
    return "\n".join([extraction.visible_text, *(value for value in values if value)])


# R3 · Beneficiario permitido ------------------------------------------------------------------------------------


def beneficiary(ctx: RuleContext) -> RuleCheck:
    match, read_name = ctx.match, ctx.invoice.supplier_name
    if match.name_lookalike is not None:
        lookalike = match.name_lookalike
        return check(
            "R3",
            RuleOutcome.ESCALATE,
            f"El nombre «{read_name}» coincide con {lookalike.name} de la lista, pero la identificación fiscal "
            f"leída ({ctx.invoice.supplier_tax_id}) no es la registrada ({lookalike.tax_id}).",
            fix=f"se confirmara con {lookalike.name}, por un canal conocido, que la factura es suya",
        )
    if match.beneficiary is None:
        who = f"«{read_name}»" if read_name else "El proveedor (sin nombre legible)"
        tax_id = f" (identificación {ctx.invoice.supplier_tax_id})" if ctx.invoice.supplier_tax_id else ""
        return check(
            "R3",
            RuleOutcome.ESCALATE,
            f"{who}{tax_id} no está en la lista de beneficiarios permitidos.",
            fix=f"{who} estuviera en la lista de beneficiarios permitidos",
        )
    known = match.beneficiary
    if not known.allowed:
        return check(
            "R3",
            RuleOutcome.ESCALATE,
            f"{known.name} (identificación {known.tax_id}) está bloqueado en la lista de beneficiarios.",
            fix=f"{known.name} no estuviera bloqueado",
        )
    return check(
        "R3",
        RuleOutcome.PASS,
        f"{known.name} (identificación {known.tax_id}) está en la lista de beneficiarios permitidos.",
        beneficiary_id=known.id,
    )


# R4 · Cuenta registrada -----------------------------------------------------------------------------------------


def account(ctx: RuleContext) -> RuleCheck:
    known, read = ctx.match.beneficiary, ctx.invoice.account_number
    if known is None:
        return check("R4", RuleOutcome.SKIPPED, "No aplica: sin beneficiario de la lista no hay cuenta registrada.")
    if read is None:
        return check("R4", RuleOutcome.SKIPPED, "No se leyó la cuenta; no se puede comparar con la registrada.")
    registered = _account_text(known)
    if normalize_code(read) != normalize_code(known.account_number):
        bank = ctx.extraction.bank_name.value
        asked = f"{bank} {read}" if bank else f"la cuenta {read}"
        return check(
            "R4",
            RuleOutcome.HOLD,
            f"La factura pide pagar a {asked}; la cuenta registrada de {known.name} es {registered}.",
            fix=f"la cuenta fuera la registrada ({registered}) o el cambio se verificara con el proveedor",
        )
    return check("R4", RuleOutcome.PASS, f"Paga a la cuenta registrada de {known.name}: {registered}.")


def _account_text(known: Beneficiary) -> str:
    return f"{known.bank_name} {known.account_number}"


# R5 · Sin cobro duplicado ---------------------------------------------------------------------------------------


def duplicate(ctx: RuleContext) -> RuleCheck:
    window = ctx.policy.duplicate_window_days
    same_number = _same_number(ctx)
    if same_number is not None:
        return check(
            "R5",
            RuleOutcome.HOLD,
            f"Ya hay un cobro de {ctx.supplier} con el mismo número ({ctx.invoice.invoice_number}) "
            f"del {day_month(same_number.on)}.",
            fix=f"una persona confirmara que no es el mismo cobro del {day_month(same_number.on)}",
            duplicate_of=same_number.invoice_id,
        )
    same_amount = _same_amount(ctx)
    if same_amount is not None and same_amount.amount is not None and same_amount.currency is not None:
        return check(
            "R5",
            RuleOutcome.HOLD,
            f"Ya hay un cobro de {ctx.supplier} por {money(same_amount.amount, same_amount.currency)} del "
            f"{day_month(same_amount.on)} ({_distance(same_amount, ctx)}), dentro de la ventana de {window} días.",
            fix=f"una persona confirmara que no es el mismo cobro del {day_month(same_amount.on)}",
            duplicate_of=same_amount.invoice_id,
        )
    return check(
        "R5",
        RuleOutcome.PASS,
        f"No hay otro cobro de {ctx.supplier} con el mismo número, ni por el mismo monto (±0,5 %) "
        f"en una ventana de {window} días.",
    )


def _same_number(ctx: RuleContext) -> Charge | None:
    number = normalize_code(ctx.invoice.invoice_number or "")
    if not number:
        return None
    return next((c for c in ctx.earlier if c.invoice_number and normalize_code(c.invoice_number) == number), None)


def _same_amount(ctx: RuleContext) -> Charge | None:
    amount, currency = ctx.invoice.amount, ctx.invoice.currency
    if amount is None or currency is None:
        return None
    window = ctx.policy.duplicate_window_days
    return next(
        (
            c
            for c in ctx.earlier
            if c.currency == currency
            and c.amount is not None
            and abs(c.amount - amount) <= DUPLICATE_AMOUNT_TOLERANCE * amount
            and abs((ctx.invoice.received_on - c.on).days) <= window
        ),
        None,
    )


def _distance(charge: Charge, ctx: RuleContext) -> str:
    days = (ctx.invoice.received_on - charge.on).days
    if days == 0:
        return "el mismo día"
    return f"{counted(abs(days), 'día', 'días')} {'antes' if days > 0 else 'después'}"


# R6 · Coincide con lo acordado ----------------------------------------------------------------------------------


def agreement(ctx: RuleContext) -> RuleCheck:
    known, amount, currency = ctx.match.beneficiary, ctx.invoice.amount, ctx.invoice.currency
    if known is None:
        return check("R6", RuleOutcome.SKIPPED, "No aplica: sin beneficiario de la lista no hay acuerdo.")
    deal = known.agreement
    if deal is None:
        return check(
            "R6",
            RuleOutcome.PASS,
            f"{known.name} no tiene un monto acordado; siguen aplicando los topes generales.",
        )
    if amount is None or currency is None:
        return check(
            "R6", RuleOutcome.SKIPPED, "No se leyó el monto o la moneda; no se puede comparar con lo acordado."
        )
    if currency != deal.currency:
        return check(
            "R6",
            RuleOutcome.ESCALATE,
            f"Lo acordado con {known.name} es en {deal.currency}; la factura viene en {currency}.",
            fix=f"la factura viniera en {deal.currency}, la moneda acordada",
        )
    if deal.kind is AgreementKind.FIXED:
        tolerance = deal.tolerance_pct if deal.tolerance_pct is not None else ctx.policy.agreement_tolerance_pct
        return _fixed_agreement(known.name, deal.amount, amount, currency, tolerance)
    return _monthly_cap(ctx, known.name, deal.amount, amount, currency)


def _fixed_agreement(name: str, agreed: Decimal, amount: Decimal, currency: str, tolerance: Decimal) -> RuleCheck:
    if agreed <= 0:
        return check(
            "R6",
            RuleOutcome.ESCALATE,
            f"El acuerdo con {name} no tiene un monto válido ({money(agreed, currency)}).",
            fix=f"el acuerdo con {name} tuviera un monto válido",
        )
    deviation = (amount - agreed) / agreed * HUNDRED
    terms = (
        f"lo acordado con {name} es {money(agreed, currency)} por factura; esta pide {money(amount, currency)} "
        f"({signed_percent(deviation)}, tolerancia {plus_minus_percent(tolerance)})"
    )
    if abs(amount - agreed) * HUNDRED > agreed * tolerance:
        low, high = agreed * (HUNDRED - tolerance) / HUNDRED, agreed * (HUNDRED + tolerance) / HUNDRED
        return check(
            "R6",
            RuleOutcome.ESCALATE,
            f"No coincide: {terms}.",
            fix=f"el monto estuviera entre {money(low, currency)} y {money(high, currency)}",
            deviation_pct=deviation,
        )
    return check("R6", RuleOutcome.PASS, f"Coincide: {terms}.", deviation_pct=deviation)


def _monthly_cap(ctx: RuleContext, name: str, cap: Decimal, amount: Decimal, currency: str) -> RuleCheck:
    received = ctx.invoice.received_on
    already = sum(
        (
            c.amount
            for c in ctx.earlier
            if c.paid and c.amount is not None and c.currency == currency and same_month(c.on, received)
        ),
        Decimal(0),
    )
    month_total = already + amount
    if month_total > cap:
        return check(
            "R6",
            RuleOutcome.ESCALATE,
            f"El tope acordado con {name} es {money(cap, currency)} al mes; con esta factura "
            f"{month_name(received)} llegaría a {money(month_total, currency)}.",
            fix=f"lo cobrado en el mes no pasara de {money(cap, currency)} (ya van {money(already, currency)})",
            month_total=month_total,
        )
    return check(
        "R6",
        RuleOutcome.PASS,
        f"Dentro del tope acordado con {name}: {month_name(received)} llegaría a {money(month_total, currency)} "
        f"de {money(cap, currency)}.",
        month_total=month_total,
    )


# R7 · Sin pagos fraccionados ------------------------------------------------------------------------------------


def split(ctx: RuleContext) -> RuleCheck:
    amount_base, threshold = ctx.invoice.amount_base, ctx.policy.approval_threshold
    base, days = ctx.policy.base_currency, ctx.policy.split_window_days
    if amount_base is None:
        return _skipped_without_base("R7", base)
    pieces = _pieces_under(threshold, ctx.nearby)
    total = sum((piece.amount_base for piece in pieces if piece.amount_base is not None), Decimal(0))
    if amount_base <= threshold and len(pieces) >= 2 and total > threshold:
        return check(
            "R7",
            RuleOutcome.ESCALATE,
            f"{ctx.supplier} mandó {len(pieces)} cobros en una ventana de {days} días que juntos suman "
            f"{money(total, base)}; cada uno queda bajo el tope de aprobación de {money(threshold, base)}, "
            "pero juntos lo superan.",
            fix=f"una persona confirmara que los {len(pieces)} cobros de {ctx.supplier} son independientes",
            pieces=len(pieces),
            total_base=total,
        )
    return check(
        "R7",
        RuleOutcome.PASS,
        f"No hay cobros de {ctx.supplier} partidos para quedar bajo el tope de {money(threshold, base)} "
        f"en una ventana de {days} días.",
    )


def _pieces_under(threshold: Decimal, charges: tuple[Charge, ...]) -> list[Charge]:
    """One charge per invoice number (a resent copy is not a second piece), each at or under the threshold."""
    by_number: dict[str, Charge] = {}
    for charge in charges:
        if charge.amount_base is not None and charge.amount_base <= threshold:
            by_number.setdefault(normalize_code(charge.invoice_number or "") or charge.invoice_id, charge)
    return list(by_number.values())


# R8 · Moneda permitida ------------------------------------------------------------------------------------------


def currency(ctx: RuleContext) -> RuleCheck:
    code, base = ctx.invoice.currency, ctx.policy.base_currency
    allowed = ", ".join(ctx.policy.allowed_currencies)
    if code is None:
        return check("R8", RuleOutcome.SKIPPED, "No se leyó la moneda.")
    if code not in ctx.policy.allowed_currencies:
        asked = f"; la factura pide {money(ctx.invoice.amount, code)}" if ctx.invoice.amount else ""
        return check(
            "R8",
            RuleOutcome.HOLD,
            f"{code} no está entre las monedas permitidas ({allowed}){asked}.",
            fix=f"{code} estuviera entre las monedas permitidas",
        )
    rate = ctx.fx.get(code)
    if rate is None or rate <= 0:
        return check(
            "R8",
            RuleOutcome.HOLD,
            f"{code} está permitida, pero no hay una tasa de cambio a {base} para convertirla.",
            fix=f"hubiera una tasa de cambio de {code} a {base}",
        )
    if code == base:
        return check("R8", RuleOutcome.PASS, f"{code} es la moneda base y está permitida ({allowed}).")
    return check(
        "R8",
        RuleOutcome.PASS,
        f"{code} es una moneda permitida ({allowed}); tasa: {money(rate, code)} por {base} 1.",
    )


# R9–R12 · money rules, in base currency -------------------------------------------------------------------------


def approval(ctx: RuleContext) -> RuleCheck:
    amount_base, threshold, base = ctx.invoice.amount_base, ctx.policy.approval_threshold, ctx.policy.base_currency
    if amount_base is None:
        return _skipped_without_base("R9", base)
    shown = money_with_base(ctx.invoice.amount, ctx.invoice.currency, amount_base, base)
    if amount_base > threshold:
        return check(
            "R9",
            RuleOutcome.ESCALATE,
            f"{shown} supera el tope de aprobación automática de {money(threshold, base)}.",
            fix=f"el monto fuera de {money(threshold, base)} o menos (la factura pide {money(amount_base, base)})",
            amount_base=amount_base,
        )
    return check(
        "R9",
        RuleOutcome.PASS,
        f"{shown} está dentro del tope de aprobación automática de {money(threshold, base)}.",
        amount_base=amount_base,
    )


def limit(ctx: RuleContext) -> RuleCheck:
    amount_base, cap, base = ctx.invoice.amount_base, ctx.policy.per_payment_limit, ctx.policy.base_currency
    if amount_base is None:
        return _skipped_without_base("R10", base)
    if amount_base > cap:
        return check(
            "R10",
            RuleOutcome.ESCALATE,
            f"{money(amount_base, base)} supera el límite por pago de {money(cap, base)}.",
            fix=f"el monto fuera de {money(cap, base)} o menos",
        )
    return check(
        "R10", RuleOutcome.PASS, f"{money(amount_base, base)} está dentro del límite por pago de {money(cap, base)}."
    )


def budget(ctx: RuleContext) -> RuleCheck:
    amount_base, cupo, base = ctx.invoice.amount_base, ctx.policy.period_budget, ctx.policy.base_currency
    if amount_base is None:
        return _skipped_without_base("R11", base)
    month, total = month_name(ctx.invoice.received_on), ctx.spent_auto + amount_base
    if total > cupo:
        return check(
            "R11",
            RuleOutcome.ESCALATE,
            f"Con este pago, lo que el agente pagó solo en {month} llegaría a {money(total, base)}; "
            f"su cupo del mes es {money(cupo, base)}.",
            fix=f"el cupo de {month} tuviera {money(total - cupo, base)} más",
            spent_after=total,
        )
    return check(
        "R11",
        RuleOutcome.PASS,
        f"Lo pagado solo por el agente en {month} quedaría en {money(total, base)} de su cupo de {money(cupo, base)}.",
        spent_after=total,
    )


def reserve(ctx: RuleContext) -> RuleCheck:
    amount_base, base = ctx.invoice.amount_base, ctx.policy.base_currency
    if amount_base is None:
        return _skipped_without_base("R12", base)
    after, floor = ctx.balance - amount_base, ctx.policy.reserve
    if after < floor:
        return check(
            "R12",
            RuleOutcome.HOLD,
            f"Pagar {money(amount_base, base)} dejaría el saldo en {money(after, base)}, debajo de la reserva de "
            f"{money(floor, base)}.",
            fix=f"el saldo tuviera {money(floor - after, base)} más (hay {money(ctx.balance, base)})",
            balance_after=after,
        )
    return check(
        "R12",
        RuleOutcome.PASS,
        f"Pagar {money(amount_base, base)} deja el saldo en {money(after, base)}, sin bajar de la reserva de "
        f"{money(floor, base)}.",
        balance_after=after,
    )


def _skipped_without_base(rule_id: str, base: str) -> RuleCheck:
    return check(rule_id, RuleOutcome.SKIPPED, f"No aplica: no hay un monto confiable en {base}.")


EVALUATORS: Mapping[str, Callable[[RuleContext], RuleCheck]] = {
    "R1": reading,
    "R2": instructions,
    "R3": beneficiary,
    "R4": account,
    "R5": duplicate,
    "R6": agreement,
    "R7": split,
    "R8": currency,
    "R9": approval,
    "R10": limit,
    "R11": budget,
    "R12": reserve,
}
