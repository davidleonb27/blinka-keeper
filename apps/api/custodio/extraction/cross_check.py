"""Compare the first reading with an independent second one, field by field, and say whether they agree.

The second reading starts before the first one and runs beside it, so it adds cost but almost no latency. Without
Gemini, the code reader (`labels`) also votes on every field it read from a document with text. A second reading
that fails, times out or has no budget is not skipped: it becomes `unavailable`, and R1 sends the invoice to a person.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from custodio import llm
from custodio.config import get_settings
from custodio.contracts import (
    CrossCheckStatus,
    ExtractedField,
    FieldCrossCheck,
    ReaderValue,
    ReadingCrossCheck,
)
from custodio.engine.cross_check import values_agree
from custodio.extraction import labels, second_reading
from custodio.extraction.amounts import parse_amount
from custodio.extraction.errors import AmountFormatError, MalformedReading
from custodio.extraction.source import SourceText
from custodio.extraction.structure import FIELD_KINDS, FieldReading, QuotedValue
from custodio.extraction.verify import normalize_value

_WORKERS = 8
_pool = ThreadPoolExecutor(max_workers=_WORKERS, thread_name_prefix="second-reader")
PendingReading = Future[second_reading.SecondReading]


def start(document: second_reading.Document) -> PendingReading | None:
    """Begin the second reading of `document`, or None in a deployment without a model (nothing to compare with)."""
    if not get_settings().anthropic_configured:
        return None
    return _pool.submit(second_reading.read, document)


def compare(first: FieldReading, pending: PendingReading, *, source: SourceText | None) -> ReadingCrossCheck:
    """Wait for the second reading and compare it with `first`. `source`: the document's own text, when it has one."""
    try:
        second = pending.result(timeout=get_settings().second_reading_timeout_seconds)
    except FutureTimeout:
        return _unavailable("el segundo lector no respondió a tiempo")
    except llm.LLMBudgetExceeded:
        return _unavailable("no queda presupuesto diario para el segundo lector")
    except (llm.LLMError, MalformedReading) as error:
        return _unavailable(f"el segundo lector falló: {error}")
    except Exception as error:  # whatever breaks the second reader, the invoice goes to a person
        return _unavailable(f"el segundo lector falló ({type(error).__name__})")
    readers = [_first_values(first), _second_values(second)]
    if source is not None and not get_settings().gemini_configured:
        readers.append(_code_values(labels.read_fields(source)))
    fields = [_field(name, [reader[name] for reader in readers if name in reader]) for name in second_reading.COMPARED]
    status = CrossCheckStatus.AGREE if all(f.agree for f in fields) else CrossCheckStatus.DISAGREE
    return ReadingCrossCheck(status=status, fields=fields)


def _unavailable(why: str) -> ReadingCrossCheck:
    return ReadingCrossCheck(status=CrossCheckStatus.UNAVAILABLE, error=why)


def _field(name: str, readings: list[ReaderValue]) -> FieldCrossCheck:
    agree = values_agree(name, [reading.value for reading in readings])
    return FieldCrossCheck.model_validate({"field": name, "readings": readings, "agree": agree})


def _first_values(first: FieldReading) -> dict[str, ReaderValue]:
    return {name: _from_field(first.model, first.fields[name]) for name in second_reading.COMPARED}


def _code_values(code: FieldReading) -> dict[str, ReaderValue]:
    """Only what the labels reader actually read and verified: a field without a label is not a vote."""
    read = {name: code.fields[name] for name in second_reading.COMPARED}
    return {name: _from_field(code.model, field) for name, field in read.items() if field.value and field.verified}


def _from_field(reader: str, field: ExtractedField) -> ReaderValue:
    return ReaderValue(reader=reader, value=field.value, quote=field.evidence.quote if field.evidence else None)


def _second_values(second: second_reading.SecondReading) -> dict[str, ReaderValue]:
    return {
        name: ReaderValue(reader=second.reader, value=_normalized(name, quoted), quote=quoted.quote)
        for name, quoted in second.fields.items()
    }


def _normalized(name: str, quoted: QuotedValue) -> str | None:
    """The second reader's value in the first reader's canonical form; kept as written when it has none."""
    if quoted.value is None or not quoted.value.strip():
        return None
    canonical = normalize_value(FIELD_KINDS[name], quoted.value)
    if canonical is None and name == "amount":
        canonical = _latin_amount(quoted.value)
    return canonical or quoted.value.strip()


def _latin_amount(written: str) -> str | None:
    try:
        return f"{parse_amount(written):f}"
    except AmountFormatError:
        return None
