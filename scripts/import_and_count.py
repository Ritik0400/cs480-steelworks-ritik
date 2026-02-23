from pathlib import Path
from steelworks import data_import, database, models
from sqlalchemy import select, func

# initialize
database.init_db()

# load sample spreadsheets
print("loading samples...")
data_import.load_all_samples(Path("data/sample"))
print("done importing")

with database.get_session() as sess:
    for tbl in [models.ProductionRecord, models.InspectionRecord, models.ShippingRecord, models.Lot]:
        cnt = sess.execute(select(func.count()).select_from(tbl)).scalar()
        print(tbl.__tablename__, cnt)
