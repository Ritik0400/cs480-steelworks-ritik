"""Pytest suite verifying the business logic (services) against acceptance
criteria.

Each test is annotated with which ACs it exercises.  The database is reset for
each function using the in-memory SQLite default.
"""

from datetime import date, timedelta

import pytest

from steelworks import database, services
from steelworks import repository
from steelworks.lot_utils import normalize_lot_id


@pytest.fixture(autouse=True)
def init_db():
    """Ensure a fresh schema for every test.

    Using the module-level ``DATABASE_URL`` default means we get an in-memory
    SQLite instance; tables are re-created before each test.
    """

    database.init_db()
    yield
    # nothing to tear down because the database is transient


def seed_inspection():
    """Insert inspection rows for three lines over two weeks.

    Returns the lot ids used (normalized strings).  This seeds AC1-AC4.
    """

    rows = []
    base = date(2023, 1, 1)
    # two weeks of data, two defect codes, three lines
    for i in range(14):
        day = base + timedelta(days=i)
        for line in ["A", "B", "C"]:
            rows.append(
                {
                    "Lot_ID": f"L{i:03}",
                    "Production_Line": line,
                    "Inspection_Date": day,
                    "Inspection_Time": None,
                    "Inspector": "X",
                    "Part_Number": "P1",
                    "Defect_Code": "D1" if i % 2 == 0 else "D2",
                    "Defect_Description": "",
                    "Severity": "",
                    "Qty_Checked": 100,
                    "Qty_Defects": 1,
                    "Disposition": None,
                    "Notes": None,
                }
            )
    services.import_inspection_data(rows)
    # normalization is idempotent
    return [normalize_lot_id(r["Lot_ID"]) for r in rows]


def test_filter_by_date_and_line():
    """AC1 & AC2 & AC3: filters should apply correctly and ranking by defects.
    """

    seed_inspection()
    # if we ask for only the first week and line B
    start = date(2023, 1, 1)
    end = date(2023, 1, 7)
    result = services.get_defect_summary(start=start, end=end, line="B")
    # line B should appear once with 7 records (one per day)
    assert result == [("B", 7)]

    # without line filter, we expect three lines, each with 7 defects
    all_result = services.get_defect_summary(start=start, end=end)
    assert set(all_result) == {("A", 7), ("B", 7), ("C", 7)}
    # ensure sorted descending (it doesn't matter since counts equal but function
    # sorts anyway)
    assert all_result[0][1] >= all_result[-1][1]


def test_trending_defects():
    """AC1 & AC4: weekly grouping of defect counts.
    """

    seed_inspection()
    trends = services.get_defect_trends()
    # we generated two defect codes alternating daily; with 14 days and 3 lines,
    # each week should show 21 of each defect.
    # weeks: 2022-W52 (Jan1 is ISO week 52 of previous year) and 2023-W01
    weeks = {week for week, _, _ in trends}
    assert "2022-W52" in weeks and "2023-W01" in weeks
    # check counts
    for week, defect, count in trends:
        assert count == 21


def test_shipping_lookup_and_lot_normalization():
    """AC5 & AC6: lots should be normalized and status retrieved correctly.
    """

    # insert a shipping record
    with database.get_session() as sess:
        lot = repository.get_or_create_lot(sess, "Lot-100")
        sess.add(
            repository.models.ShippingRecord(
                lot_id=lot.id,
                ship_date=date(2023, 3, 1),
                sales_order_no="SO1",
                customer="C1",
                destination_state="WA",
                carrier="FedEx",
                bol_no="BOL1",
                tracking_pro=None,
                qty_shipped=100,
                ship_status="Shipped",
            )
        )
    # lookup with different formatting
    res = services.lookup_shipment("lot 100")
    assert res == (True, date(2023, 3, 1))
    # ensure normalization is consistent even during creation
    with database.get_session() as sess:
        l1 = repository.get_or_create_lot(sess, "Lot-100")
        l2 = repository.get_or_create_lot(sess, "LOT 100")
        assert l1.id == l2.id
    # searching a non-existent lot yields None
    assert services.lookup_shipment("not-a-lot") is None

