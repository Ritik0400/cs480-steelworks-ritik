from pathlib import Path
from steelworks import data_import, database

# ensure database exists
database.init_db()

print("importing files...")
data_import.load_all_samples(Path("data/sample"))
print("import finished")
