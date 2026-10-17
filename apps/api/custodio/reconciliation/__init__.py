"""Bank reconciliation and month-end close. Owned by lane L14.

The model reads statements; code pairs and closes; a person reviews. A CSV export is read by code alone
(`read_csv_statement`); a PDF or an image is read by Claude through `custodio.llm.structured` and every row is
checked against the document's own text (`read_statement_document`). `reconcile` pairs movements with payments in a
fixed order of levels; `summarize` and `evidence_pack` close the month. All of it is pure except the model reading.
"""

from custodio.reconciliation.csv_statement import read_csv_statement
from custodio.reconciliation.document_statement import read_statement_document
from custodio.reconciliation.evidence import EvidenceSource, evidence_pack
from custodio.reconciliation.match import reconcile
from custodio.reconciliation.summary import summarize

__all__ = [
    "EvidenceSource",
    "evidence_pack",
    "read_csv_statement",
    "read_statement_document",
    "reconcile",
    "summarize",
]
