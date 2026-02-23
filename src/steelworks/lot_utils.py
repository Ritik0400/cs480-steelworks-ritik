"""Utility helpers for working with lot identifiers.

Lot IDs may be formatted inconsistently across different source spreadsheets
(e.g. "LOT-123" vs "lot 123" vs "123").  To allow flexible searching we
normalize identifiers by removing non-alphanumeric characters and converting to
upper case (AC6).  The normalization is O(k) where k is the length of the input
string.
"""

import re


def normalize_lot_id(raw: str) -> str:
    """Return a canonical form of a lot identifier.

    Removes whitespace and punctuation, uppercases the result.  Examples::

        >>> normalize_lot_id("Lot-001 A")
        'LOT001A'

    This function should be called consistently before persisting or querying
    lot identifiers so that semantically-equivalent values match.
    """
    if raw is None:
        return ""
    # keep letters and digits only
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw)
    return cleaned.upper()
