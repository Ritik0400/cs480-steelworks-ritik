"""Data access layer (repositories) for SteelWorks.

All direct interactions with SQLAlchemy sessions and queries live here.  The
service layer imports these functions to implement business rules without
worrying about SQL details.

Each function that opens a session uses ``database.get_session`` context manager
so that connections are properly closed and transactions managed.  Complexity
of these functions is generally O(n) where ``n`` is the number of rows scanned,
but indexes (created in schema.sql) keep most lookups closer to O(log n).
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import database, models
from .lot_utils import normalize_lot_id


# region helper / CRUD

def get_or_create_lot(session: Session, lot: str) -> models.Lot:
    """Return a persistent ``Lot`` instance matching ``lot`` string.

    The ``lot`` argument is normalized (see :func:`normalize_lot_id`) so that
different formatting still resolves to the same record.  The lookup is
performed in-memory after the normalization; insertion is O(1).
    """

    normalized = normalize_lot_id(lot)
    existing = session.execute(
        select(models.Lot).where(models.Lot.lot == normalized)
    ).scalar_one_or_none()
    if existing:
        return existing
    new = models.Lot(lot=normalized)
    session.add(new)
    session.flush()  # populate new.id
    return new


def get_or_create_line(session: Session, line: str) -> models.ProductionLine:
    """Return or create a production line record.

    Line names are treated case-insensitively but stored canonically.
    If ``line`` is None or empty, returns a default line ("UNKNOWN").
    """

    # handle None or empty input gracefully
    if not line:
        line = "UNKNOWN"
    canon = line.strip().upper()
    existing = session.execute(
        select(models.ProductionLine).where(models.ProductionLine.line == canon)
    ).scalar_one_or_none()
    if existing:
        return existing
    new = models.ProductionLine(line=canon)
    session.add(new)
    session.flush()
    return new


def get_or_create_defect(session: Session, code: str) -> models.Defect:
    """Return or create a defect type record.
    
    If ``code`` is None or empty, returns a default defect ("UNKNOWN").
    """

    # handle None or empty input gracefully
    if not code:
        code = "UNKNOWN"
    canon = code.strip().upper()
    existing = session.execute(
        select(models.Defect).where(models.Defect.defect_code == canon)
    ).scalar_one_or_none()
    if existing:
        return existing
    new = models.Defect(defect_code=canon)
    session.add(new)
    session.flush()
    return new


# endregion


# region query helpers for summaries

def summary_defects_by_line(
    start: Optional[date] = None,
    end: Optional[date] = None,
    line: Optional[str] = None,
) -> List[Tuple[str, int]]:
    """Return defect totals grouped by production line.

    Results are sorted descending by total defects (AC3).

    Parameters
    ----------
    start, end: Optional[date]
        If provided, filter inspection records to those dates (inclusive).
    line: Optional[str]
        If provided, limit to this production line (case-insensitive).

    Returns
    -------
    List of tuples of (production_line, total_defects).

    Complexity: single SQL query with GROUP BY; typical cost O(m log n)
    where ``n`` is number of inspection rows and ``m`` number of lines.
    """

    with database.get_session() as sess:
        # join production lines to inspection records via the foreign key
        stmt = (
            select(models.ProductionLine.line, func.sum(models.InspectionRecord.qty_defects))
            .join(
                models.InspectionRecord,
                models.ProductionLine.id == models.InspectionRecord.production_line_id,
            )
        )
        if start:
            stmt = stmt.where(models.InspectionRecord.inspection_date >= start)
        if end:
            stmt = stmt.where(models.InspectionRecord.inspection_date <= end)
        if line:
            stmt = stmt.where(func.upper(models.ProductionLine.line) == line.strip().upper())
        stmt = stmt.group_by(models.ProductionLine.line)
        stmt = stmt.order_by(func.sum(models.InspectionRecord.qty_defects).desc())
        results = sess.execute(stmt).all()
    # results is list of Row; convert to simple tuples
    return [(r[0], int(r[1] or 0)) for r in results]


def trending_defects(
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> List[Tuple[str, str, int]]:
    """Return defect counts grouped by ISO week and defect code (AC4).

    When the database supports ``to_char`` (PostgreSQL) we could push the
    grouping into SQL, but for portability (SQLite in tests) we instead load the
    raw date/code pairs and aggregate in Python.  This avoids relying on
    database-specific functions.

    Time complexity is O(n) where ``n`` is the number of matching inspection
    records; space complexity is O(k) where ``k`` is the number of distinct
    (week,defect) combinations.
    """

    from collections import defaultdict
    import datetime

    with database.get_session() as sess:
        stmt = select(
            models.InspectionRecord.inspection_date,
            models.Defect.defect_code,
            models.InspectionRecord.qty_defects,
        ).join(models.Defect, models.InspectionRecord.defect)
        if start:
            stmt = stmt.where(models.InspectionRecord.inspection_date >= start)
        if end:
            stmt = stmt.where(models.InspectionRecord.inspection_date <= end)
        rows = sess.execute(stmt).all()

    # aggregate in Python
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for insp_date, code, qty in rows:
        if insp_date is None:
            continue
        # ISO week string as YYYY-Www
        year, week, _ = insp_date.isocalendar()
        key = (f"{year}-W{week:02}", code)
        counts[key] += qty or 0
    # convert to sorted list
    result: List[Tuple[str, str, int]] = []
    for (week_str, defect_code), total in sorted(counts.items()):
        result.append((week_str, defect_code, total))
    return result


def shipping_status_for_lot(lot_query: str) -> Optional[Tuple[bool, date]]:
    """Return whether ``lot_query`` has shipped and the most recent ship date.

    ``lot_query`` is normalized to match stored lot identifiers (AC6).  Returns a
    tuple ``(shipped, ship_date)`` if any shipments exist; ``None`` otherwise.

    Complexity: queries by lot index, O(log n).
    """

    normalized = normalize_lot_id(lot_query)
    with database.get_session() as sess:
        lot = sess.execute(
            select(models.Lot).where(models.Lot.lot == normalized)
        ).scalar_one_or_none()
        if lot is None:
            return None
        # find the latest ship_date for this lot
        stmt = (
            select(models.ShippingRecord.ship_date, models.ShippingRecord.ship_status)
            .where(models.ShippingRecord.lot_id == lot.id)
            .order_by(models.ShippingRecord.ship_date.desc())
            .limit(1)
        )
        row = sess.execute(stmt).first()
        if row:
            shipped = row[1] == 'Shipped'
            return shipped, row[0]
        return None

# endregion
