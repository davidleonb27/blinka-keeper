from __future__ import annotations


class ReceiptKeyError(ValueError):
    """The configured signing key cannot be used. Raised at startup, never with the key in the message."""
