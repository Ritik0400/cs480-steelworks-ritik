import pytest

from steelworks.utils import normalize_lot_id


def test_normalize_lot_id_basic():
    # simple alphanumeric input should be uppercased
    assert normalize_lot_id("abc123") == "ABC123"


def test_normalize_lot_id_strip_non_alphanumeric():
    # hyphens, spaces, and other characters are removed
    assert normalize_lot_id("ab-c 12_3!") == "ABC123"
