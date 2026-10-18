"""Reads a decision's failing rules and splits them into what the supplier can fix and what is never negotiated.

Pure: the decision, its reading and the policy in, an Assessment out. The texts are built from the rule's facts and
the registered agreement, never from the document's words, so an invoice cannot write the message sent about it.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from custodio.contracts import (
    RULES,
    AgreementKind,
    Beneficiary,
    Decision,
    ExtractedField,
    ExtractedInvoice,
    Policy,
    RuleOutcome,
    RuleResult,
)
from custodio.corrections.form import form_issues
from custodio.corrections.models import Assessment, Blocker, BlockerKind, CorrectableField, Issue, IssueKind
from custodio.engine.formatting import money
from custodio.extraction.amounts import currencies_named, has_bare_dollar

FAILED = (RuleOutcome.HOLD, RuleOutcome.ESCALATE)
CURRENCY_CODE = re.compile(r"[A-Z]{3}")
UPLOAD_ONLY_FIELDS = {"supplier_name": "el nombre del proveedor", "supplier_tax_id": "la identificación fiscal"}
ACCOUNT_FIELD = "account_number"
LABELS = {spec.id: spec.label for spec in RULES}

WHY_NOT: dict[BlockerKind, str] = {
    BlockerKind.ACCOUNT_CHANGED: (
        "La cuenta de la factura no es la registrada. Un cambio de cuenta nunca se negocia por el canal que lo pide: "
        "una persona lo verifica con el contacto registrado."
    ),
    BlockerKind.BANK_DETAILS: (
        "Los datos bancarios no pasan el control del riel. Pedírselos al proveedor por un enlace abriría la puerta a "
        "cambiar la cuenta; una persona los verifica con el contacto registrado."
    ),
    BlockerKind.DUPLICATE: (
        "Parece un cobro repetido. Una corrección no puede convertirlo en un cobro nuevo: lo revisa una persona."
    ),
    BlockerKind.HIDDEN_INSTRUCTION: (
        "El documento trae instrucciones dirigidas al agente. A quien intenta manipularlo no se le abre un canal "
        "para volver a intentarlo."
    ),
    BlockerKind.UNREGISTERED_SUPPLIER: (
        "El proveedor no está registrado o está bloqueado. Blinka Keeper sólo escribe a proveedores registrados; "
        "darlo de alta lo decide una persona de la empresa."
    ),
    BlockerKind.SANCTIONS: (
        "El nombre coincide con la lista OFAC. Eso no se corrige con un documento: lo revisa una persona."
    ),
    BlockerKind.SENDER_DOMAIN: (
        "El correo viene de un dominio parecido al registrado, la marca de una suplantación. No se le responde a ese "
        "remitente."
    ),
    BlockerKind.SPLIT: "Parece un cobro partido para quedar bajo el tope de aprobación. Lo revisa una persona.",
    BlockerKind.RESERVE: "Pagarla dejaría el saldo bajo la reserva. Eso no depende del proveedor.",
    BlockerKind.POLICY_CURRENCY: (
        "La moneda acordada no está permitida en la política de la empresa. Lo decide la empresa, no el proveedor."
    ),
}
BLOCKING_RULES: dict[str, BlockerKind] = {
    "R2": BlockerKind.HIDDEN_INSTRUCTION,
    "R3": BlockerKind.UNREGISTERED_SUPPLIER,
    "R4": BlockerKind.ACCOUNT_CHANGED,
    "R5": BlockerKind.DUPLICATE,
    "R7": BlockerKind.SPLIT,
    "R12": BlockerKind.RESERVE,
    "R13": BlockerKind.BANK_DETAILS,
    "R14": BlockerKind.SANCTIONS,
}
FOR_A_PERSON = ("R9", "R10", "R11")  # money thresholds: a correction does not lift them


def assess(decision: Decision, extraction: ExtractedInvoice, policy: Policy, *, received_on: date) -> Assessment:
    failing = {rule.rule_id: rule for rule in decision.rules if rule.outcome in FAILED}
    if not failing:
        return Assessment(issues=[], blockers=[], still_for_a_person=[])
    known = _registered(policy, decision.beneficiary_id)
    blockers = _blockers(failing, known, policy)
    issues = [*_rule_issues(failing, decision, extraction, known, policy), *form_issues(extraction, received_on)]
    for_a_person = [LABELS[rule_id] for rule_id in FOR_A_PERSON if rule_id in failing]
    if _over_monthly_cap(failing.get("R6"), known):
        for_a_person.append(f"{LABELS['R6']} (tope mensual)")
    return Assessment(issues=_unique(issues), blockers=_unique_blockers(blockers), still_for_a_person=for_a_person)


def _registered(policy: Policy, beneficiary_id: str | None) -> Beneficiary | None:
    return next((b for b in policy.beneficiaries if b.id == beneficiary_id), None)


# Never negotiated ---------------------------------------------------------------------------------------------------


def _blockers(failing: dict[str, RuleResult], known: Beneficiary | None, policy: Policy) -> list[Blocker]:
    found = [_blocker(kind, rule_id) for rule_id, kind in BLOCKING_RULES.items() if rule_id in failing]
    if "R15" in failing:
        changed = failing["R15"].facts.get("account_changed") or "R4" in failing
        found.append(_blocker(BlockerKind.ACCOUNT_CHANGED if changed else BlockerKind.SENDER_DOMAIN, "R15"))
    if "R8" in failing and _expected_currency(known, policy) is None:
        found.append(_blocker(BlockerKind.POLICY_CURRENCY, "R8"))
    return found


def _blocker(kind: BlockerKind, rule_id: str) -> Blocker:
    return Blocker(kind=kind, rule_id=rule_id, reason=WHY_NOT[kind])


# Correctable --------------------------------------------------------------------------------------------------------


def _rule_issues(
    failing: dict[str, RuleResult],
    decision: Decision,
    extraction: ExtractedInvoice,
    known: Beneficiary | None,
    policy: Policy,
) -> list[Issue]:
    issues: list[Issue] = []
    if "R1" in failing:
        issues += _reading_issues(extraction, known, policy, amount_parsed=decision.amount is not None)
    if "R6" in failing and known is not None:
        issues += _agreement_issues(decision, known)
    if "R8" in failing and (allowed := _expected_currency(known, policy)) is not None:
        issues.append(_currency_not_allowed(decision.currency, allowed))
    return issues


def _reading_issues(
    extraction: ExtractedInvoice, known: Beneficiary | None, policy: Policy, *, amount_parsed: bool
) -> list[Issue]:
    minimum = float(policy.min_confidence)
    issues: list[Issue] = []
    if _doubtful(extraction.amount, minimum) or not amount_parsed:
        issues.append(_amount_unreadable(known))
    if _doubtful(extraction.currency, minimum) or _bare_dollar(extraction.currency):
        issues.append(_currency_unclear(known))
    unreadable = [label for name, label in UPLOAD_ONLY_FIELDS.items() if _doubtful(getattr(extraction, name), minimum)]
    if _doubtful(extraction.account_number, minimum):
        unreadable.append("la cuenta (sólo se paga a la registrada)")
    if unreadable or not issues:
        issues.append(_unreadable(unreadable))
    return issues


def _doubtful(field: ExtractedField, minimum: float) -> bool:
    return field.value is None or not field.verified or field.confidence < minimum


def _bare_dollar(field: ExtractedField) -> bool:
    quote = field.evidence.quote if field.evidence else ""
    return has_bare_dollar(quote) and not currencies_named(quote)


def _amount_unreadable(known: Beneficiary | None) -> Issue:
    deal = known.agreement if known else None
    expected = "el total escrito con claridad, en números y con su moneda"
    if deal is not None and deal.kind is AgreementKind.FIXED:
        expected = f"{money(deal.amount, deal.currency)}, el monto acordado, escrito con claridad"
    return Issue(
        kind=IssueKind.AMOUNT_UNREADABLE,
        rule_id="R1",
        fields=[CorrectableField.AMOUNT],
        problem="El monto de la factura no se pudo leer con certeza.",
        expected=expected,
    )


def _currency_unclear(known: Beneficiary | None) -> Issue:
    agreed = known.agreement.currency if known and known.agreement else None
    expected = f"la moneda escrita con su código: {agreed}" if agreed else "la moneda escrita con su código (USD, COP…)"
    return Issue(
        kind=IssueKind.CURRENCY_UNCLEAR,
        rule_id="R1",
        fields=[CorrectableField.CURRENCY],
        problem="La moneda de la factura no es clara (por ejemplo, un «$» sin código puede ser pesos o dólares).",
        expected=expected,
    )


def _unreadable(fields: list[str]) -> Issue:
    what = ", ".join(fields) if fields else "los datos de la factura"
    return Issue(
        kind=IssueKind.FIELD_UNREADABLE,
        rule_id="R1",
        fields=[],
        problem=f"No se pudo leer con certeza {what}.",
        expected="una copia legible de la factura (PDF o foto nítida)",
    )


def _agreement_issues(decision: Decision, known: Beneficiary) -> list[Issue]:
    deal, amount, currency = known.agreement, decision.amount, decision.currency
    if deal is None or amount is None or currency is None:
        return []
    if currency != deal.currency:
        return [
            Issue(
                kind=IssueKind.CURRENCY_MISMATCH,
                rule_id="R6",
                fields=[CorrectableField.AMOUNT, CorrectableField.CURRENCY],
                problem=f"La factura viene en {_code(currency)} y lo acordado con {known.name} es en {deal.currency}.",
                expected=_agreed(deal.kind, deal.amount, deal.currency),
            )
        ]
    if deal.kind is not AgreementKind.FIXED:
        return []
    return [
        Issue(
            kind=IssueKind.AMOUNT_MISMATCH,
            rule_id="R6",
            fields=[CorrectableField.AMOUNT],
            problem=(
                f"La factura pide {money(amount, _code(currency))} y lo acordado con {known.name} es "
                f"{money(deal.amount, deal.currency)} por factura."
            ),
            expected=f"{money(deal.amount, deal.currency)}, el monto acordado",
        )
    ]


def _agreed(kind: AgreementKind, amount: Decimal, currency: str) -> str:
    if kind is AgreementKind.FIXED:
        return f"la factura en {currency}: {money(amount, currency)} por factura, lo acordado"
    return f"la factura en {currency}, la moneda acordada (tope de {money(amount, currency)} al mes)"


def _currency_not_allowed(currency: str | None, allowed: str) -> Issue:
    invoiced = f"en {_code(currency)}, " if currency else ""
    return Issue(
        kind=IssueKind.CURRENCY_NOT_ALLOWED,
        rule_id="R8",
        fields=[CorrectableField.AMOUNT, CorrectableField.CURRENCY],
        problem=f"La factura viene {invoiced}una moneda en la que la empresa no paga.",
        expected=f"la factura en {allowed}",
    )


def _expected_currency(known: Beneficiary | None, policy: Policy) -> str | None:
    """The currency a supplier should bill in, when the company pays in it; None leaves it to the company."""
    if known is None:
        return None
    wanted = known.agreement.currency if known.agreement else known.currency
    return wanted if wanted in policy.allowed_currencies else None


def _over_monthly_cap(result: RuleResult | None, known: Beneficiary | None) -> bool:
    deal = known.agreement if known else None
    return result is not None and deal is not None and deal.kind is AgreementKind.MONTHLY_CAP


# Helpers ------------------------------------------------------------------------------------------------------------


def _code(currency: str) -> str:
    """A currency as read is quoted only when it is an ISO code: the document never writes into these texts."""
    return currency if CURRENCY_CODE.fullmatch(currency) else "otra moneda"


def _unique(issues: list[Issue]) -> list[Issue]:
    return list({issue.kind: issue for issue in reversed(issues)}.values())[::-1]


def _unique_blockers(blockers: list[Blocker]) -> list[Blocker]:
    return list({blocker.kind: blocker for blocker in reversed(blockers)}.values())[::-1]
