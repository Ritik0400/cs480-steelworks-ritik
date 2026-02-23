from steelworks import database, models
from sqlalchemy import select, func

with database.get_session() as sess:
    for tbl in (models.ProductionRecord, models.InspectionRecord, models.ShippingRecord):
        cnt = sess.execute(select(func.count()).select_from(tbl)).scalar()
        print(f"{tbl.__tablename__:25} {cnt} rows")
