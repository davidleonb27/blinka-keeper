"""Typed failures of reading a bank statement. Each one carries an honest Spanish message for the person."""

from __future__ import annotations


class StatementError(Exception):
    message = "No pudimos leer el extracto."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class StatementFormatError(StatementError):
    """The file is not a statement Blinka Keeper can read: no date, description and amount columns, or no rows."""

    message = "El archivo no parece un extracto bancario."


class UnsupportedStatement(StatementError):
    message = "Sólo leemos extractos en CSV, PDF, PNG, JPEG o WEBP."
