"""Helpers for reading Excel files and importing into the database.

These functions are intended for manual use during development or testing, not as
part of the core user-facing flows.  They rely on ``pandas`` and ``openpyxl``
for convenience.

Each ``load_*`` function reads a spreadsheet into a DataFrame, does minimal
cleaning, and delegates to the service layer_importers defined in
``steelworks.services``.  Time complexity is dominated by pandas' I/O and the
subsequent insertion loops (roughly O(n) per row).
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import List

from . import services, database


def _read_excel(path: Path) -> pd.DataFrame:
    """Common helper to load a sheet into a DataFrame.

    We force ``dtype=str`` to avoid pandas inferring types that might convert
    lot ids to numbers and lose leading zeros.
    """
    return pd.read_excel(path, dtype=str)


def load_production(path: Path) -> None:
    df = _read_excel(path)
    # rename columns to expected keys used by services
    df = df.rename(columns={
        "Lot_ID": "Lot_ID",
        "Production_Line": "Production_Line",
        "Production_Date": "Production_Date",
        "Shift": "Shift",
        "Part_Number": "Part_Number",
        "Units_Planned": "Units_Planned",
        "Units_Actual": "Units_Actual",
        "Downtime_Min": "Downtime_Min",
        "Line_Issue": "Line_Issue",
        "Primary_Issue": "Primary_Issue",
        "Supervisor_Notes": "Supervisor_Notes",
    })
    services.import_production_data(df.to_dict(orient="records"))


def load_inspection(path: Path) -> None:
    df = _read_excel(path)
    df = df.rename(columns={
        "Lot_ID": "Lot_ID",
        "Production_Line": "Production_Line",
        "Inspection_Date": "Inspection_Date",
        "Inspection_Time": "Inspection_Time",
        "Inspector": "Inspector",
        "Part_Number": "Part_Number",
        "Defect_Code": "Defect_Code",
        "Defect_Description": "Defect_Description",
        "Severity": "Severity",
        "Qty_Checked": "Qty_Checked",
        "Qty_Defects": "Qty_Defects",
        "Disposition": "Disposition",
        "Notes": "Notes",
    })
    services.import_inspection_data(df.to_dict(orient="records"))


def load_shipping(path: Path) -> None:
    df = _read_excel(path)
    df = df.rename(columns={
        "Lot_ID": "Lot_ID",
        "Ship_Date": "Ship_Date",
        "Sales_Order_No": "Sales_Order_No",
        "Customer": "Customer",
        "Destination_State": "Destination_State",
        "Carrier": "Carrier",
        "BOL_No": "BOL_No",
        "Tracking_PRO": "Tracking_PRO",
        "Qty_Shipped": "Qty_Shipped",
        "Ship_Status": "Ship_Status",
        "Hold_Reason": "Hold_Reason",
        "Shipping_Notes": "Shipping_Notes",
    })
    services.import_shipping_data(df.to_dict(orient="records"))


from typing import Union


def load_all_samples(sample_dir: Union[Path, str]) -> None:
    """Convenience function to load every sample file under a directory.

    ``sample_dir`` may be either a ``Path`` or a string path; we convert to a
    ``Path`` internally.  The function inspects filename substrings to
    determine which loader to call.  It is purely a developer convenience, not
    part of the core user story.

    Files are categorized as follows:
    - *production* files: contain "production" or "prod"
    - *inspection* files: contain "inspection", "inspector", "qe", or "daily" / "weekly"
    - *shipping* files: contain "shipping" or "ship"

    Complexity is O(n) where ``n`` is the number of files in the directory.
    """

    # accept strings for easier CLI usage
    sample_dir = Path(sample_dir)

    for file in sample_dir.glob("*.xlsx"):
        name = file.name.lower()
        if "production" in name or "prod" in name:
            print(f"loading production: {file.name}")
            load_production(file)
        elif "inspection" in name or "inspector" in name or "qe" in name or "daily" in name or "weekly" in name:
            print(f"loading inspection: {file.name}")
            load_inspection(file)
        elif "shipping" in name or "ship" in name:
            print(f"loading shipping: {file.name}")
            load_shipping(file)
        else:
            print(f"Skipping {file}")
