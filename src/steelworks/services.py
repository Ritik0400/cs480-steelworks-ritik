"""Business logic layer for SteelWorks operations.

Services orchestrate repository calls and add domain-specific logic that is
not purely persistence-related.  They are independent of the UI framework, which
makes them easy to unit test.  Each service function documents which acceptance
criteria (AC) it supports.

Time/space complexity comments refer to the dominant database operations; in all
cases we push heavy lifting into SQL queries rather than Python loops.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

from . import repository
from .repository import summary_defects_by_line, trending_defects, shipping_status_for_lot


# AC1 & AC2: filtering by date range and production line

def get_defect_summary(
    start: Optional[date] = None,
    end: Optional[date] = None,
    line: Optional[str] = None,
) -> List[Tuple[str, int]]:
    """Return total defects by production line, with optional filters.

    This service wraps :func:`summary_defects_by_line` and therefore inherits
    its complexity characteristics: the cost is dominated by a single grouped
    SQL query (O(n) with respect to inspection rows).

    ACs covered: 1 (date filter), 2 (line filter), 3 (most issues by line).
    """

    return summary_defects_by_line(start=start, end=end, line=line)


def get_defect_trends(start: Optional[date] = None, end: Optional[date] = None) -> List[Tuple[str, str, int]]:
    """Return weekly defect trends (counts per defect type).

    Delegates to :func:`trending_defects`.  Filtering by date range covers AC1;
    the resulting grouping addresses AC4.
    """

    return trending_defects(start=start, end=end)


def lookup_shipment(lot_id: str) -> Optional[Tuple[bool, Optional[date]]]:
    """Check whether a lot has shipped.

    Normalizes the lot identifier and queries via
    :func:`shipping_status_for_lot`.  Supports AC5 (status by lot) and AC6
    (ID consistency).
    """

    return shipping_status_for_lot(lot_id)

# Additional helpers for import scripts are also placed here

def import_production_data(rows: List[dict]) -> None:
    """Insert production record rows returned by ``pandas.DataFrame.to_dict``.

    Skips rows with missing required fields (date, production_line, etc.) to
    avoid null-constraint violations. This helps handle messy source data
    gracefully (AC6 principle extended to data quality).

    Complexity: O(m) where m is the number of valid rows; each row lookup/insertion
    uses indexed selects so overall roughly O(m log n).
    """

    from . import database

    skipped = 0
    with database.get_session() as sess:
        for row in rows:
            # validate required fields
            if not row.get("Lot_ID") or not row.get("Production_Date") or not row.get("Production_Line"):
                skipped += 1
                continue
            lot = repository.get_or_create_lot(sess, row.get("Lot_ID"))
            line = repository.get_or_create_line(sess, row.get("Production_Line"))
            record = repository.models.ProductionRecord(
                lot_id=lot.id,
                production_line_id=line.id,
                date=row.get("Production_Date"),
                shift=row.get("Shift", "Unknown"),
                part_number=row.get("Part_Number", ""),
                units_planned=row.get("Units_Planned", 0),
                units_actual=row.get("Units_Actual", 0),
                downtime_min=row.get("Downtime_Min", 0),
                line_issue=row.get("Line_Issue", False),
                primary_issue=row.get("Primary_Issue"),
                supervisor_notes=row.get("Supervisor_Notes"),
            )
            sess.add(record)
    if skipped > 0:
        print(f"Skipped {skipped} incomplete production records")


def import_inspection_data(rows: List[dict]) -> None:
    """Insert inspection record rows and create defects if needed.

    Skips rows with missing required fields (inspection_date, lot_id, etc.).

    Complexity: O(m) where m is the valid rows.
    """

    from . import database

    skipped = 0
    with database.get_session() as sess:
        for row in rows:
            # validate required fields
            if not row.get("Lot_ID") or not row.get("Inspection_Date") or not row.get("Production_Line"):
                skipped += 1
                continue
            lot = repository.get_or_create_lot(sess, row.get("Lot_ID"))
            line = repository.get_or_create_line(sess, row.get("Production_Line"))
            defect_id = None
            if row.get("Qty_Defects", 0) and row.get("Qty_Defects", 0) > 0:
                defect_code = row.get("Defect_Code")
                if defect_code:
                    defect = repository.get_or_create_defect(sess, defect_code)
                    defect_id = defect.id
            record = repository.models.InspectionRecord(
                lot_id=lot.id,
                production_line_id=line.id,
                inspection_date=row.get("Inspection_Date"),
                inspection_time=row.get("Inspection_Time"),
                inspector=row.get("Inspector", "Unknown"),
                part_number=row.get("Part_Number", ""),
                defect_id=defect_id,
                defect_description=row.get("Defect_Description"),
                severity=row.get("Severity"),
                qty_checked=row.get("Qty_Checked", 0),
                qty_defects=row.get("Qty_Defects", 0),
                disposition=row.get("Disposition"),
                notes=row.get("Notes"),
            )
            sess.add(record)
    if skipped > 0:
        print(f"Skipped {skipped} incomplete inspection records")


def import_shipping_data(rows: List[dict]) -> None:
    """Insert shipping rows.

    Skips rows with missing required fields.
    """

    from . import database

    skipped = 0
    with database.get_session() as sess:
        for row in rows:
            # validate required fields
            if not row.get("Lot_ID") or not row.get("Ship_Date"):
                skipped += 1
                continue
            lot = repository.get_or_create_lot(sess, row.get("Lot_ID"))
            record = repository.models.ShippingRecord(
                lot_id=lot.id,
                ship_date=row.get("Ship_Date"),
                sales_order_no=row.get("Sales_Order_No", ""),
                customer=row.get("Customer", ""),
                destination_state=row.get("Destination_State", ""),
                carrier=row.get("Carrier", ""),
                bol_no=row.get("BOL_No", ""),
                tracking_pro=row.get("Tracking_PRO"),
                qty_shipped=row.get("Qty_Shipped", 0),
                ship_status=row.get("Ship_Status", "Pending"),
                hold_reason=row.get("Hold_Reason"),
                shipping_notes=row.get("Shipping_Notes"),
            )
            sess.add(record)
    if skipped > 0:
        print(f"Skipped {skipped} incomplete shipping records")
