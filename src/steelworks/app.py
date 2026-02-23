"""Streamlit application for SteelWorks reporting dashboard.

This module defines the interactive user interface.  Streamlit handles state
and rendering; we simply map widget values to service calls.  The code is
written to be readable by junior engineers, with comments explaining each step
and complexity where appropriate.

To launch the app run::

    streamlit run src/steelworks/app.py

The app assumes that a database is reachable via ``DATABASE_URL`` and that the
schema has been initialized.
"""

from __future__ import annotations

from datetime import date
from typing import List, Tuple

import streamlit as st

from steelworks import services, database


def main() -> None:
    """Entry point for the Streamlit app.  Sets up UI controls and displays
    results based on user input.
    """

    st.title("SteelWorks Operations Dashboard")

    # initialize database (in a real deployment this would be done separately)
    database.init_db()

    # sidebar filters
    st.sidebar.header("Filters")

    # choose reasonable defaults so the component always returns a date
    start_date = st.sidebar.date_input("Start date", value=date.today())
    end_date = st.sidebar.date_input("End date", value=date.today())
    line_filter = st.sidebar.text_input("Production line (optional)")

    # AC1/AC2/AC3: defect summary by line
    st.header("Defects by Production Line")
    # service returns list of tuples; we always supply start/end because they
    # are required by the ACs.  Users can set them to the same day to effectively
    # limit the range to a single date.
    summary: List[Tuple[str, int]] = services.get_defect_summary(
        start=start_date,
        end=end_date,
        line=line_filter if line_filter else None,
    )
    if summary:
        st.table(summary)
    else:
        st.write("No data for selected filters.")

    # AC4: trending defect types
    st.header("Defect Trends (weekly)")
    trends = services.get_defect_trends(start=start_date, end=end_date)
    if trends:
        # convert to DataFrame for plotting
        import pandas as pd

        df = pd.DataFrame(trends, columns=["week", "defect", "count"])
        # pivot so each defect is a column, weeks are index
        pivot = df.pivot(index="week", columns="defect", values="count").fillna(0)
        st.line_chart(pivot)
    else:
        st.write("No trends available.")

    # AC5/AC6: lot lookup
    st.header("Lot Shipping Status")
    lookup = st.text_input("Search lot ID")
    if lookup:
        result = services.lookup_shipment(lookup)
        if result is None:
            st.write("No shipments found for that lot.")
        else:
            shipped, ship_date = result
            if shipped:
                st.success(f"Lot has shipped on {ship_date}")
            else:
                st.info("Lot exists but has not shipped yet.")

    # help text
    st.sidebar.markdown(
        """
        ### Usage notes
        - Use the filters to restrict defects by calendar range and line.
        - Trend chart groups defects by ISO week (AC4).
        - Lot lookup ignores formatting differences (AC6).
        """
    )


if __name__ == "__main__":
    main()
