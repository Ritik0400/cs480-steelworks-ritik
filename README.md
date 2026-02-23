# SteelWorks Operations Dashboard

A small Python-based reporting tool that ingests production, inspection, and
shipping data from spreadsheets and provides summary-level insights for
operations analysts.  Users can filter by date range and production line, view
which lines have the most defects, examine defect trends over time, and check
shipment status for specific lots.

This project was built to satisfy the following user story and acceptance
criteria (ACs):

- **AC1 — Filter by date range:** summaries only include records within a
  selected date range.
- **AC2 — Filter by production line:** summaries can be limited to a particular
  production line.
- **AC3 — “Most issues” by line:** shows which lines incurred the most defects
  (sorted descending).
- **AC4 — Trending defect types:** defect counts over time (grouped weekly).
- **AC5 — Has a lot/batch shipped?** search for a lot ID returns status and
  ship date.
- **AC6 — Lot ID consistency handling:** search tolerates different lot ID
  formats by normalizing them.

The layered architecture (UI → service → repository → database) is described in
`docs/` alongside assumptions, data design, and architecture/tech stack
records.

---

## 🛠️ Project structure

```
cs480_steelworks-main/
├─ pyproject.toml        # Poetry config & dependencies
├─ README.md
├─ src/
│  └─ steelworks/        # application package
│     ├─ __init__.py
│     ├─ app.py          # streamlit UI entrypoint
│     ├─ database.py     # engine & session management
│     ├─ data_import.py  # helpers to load sample spreadsheets
│     ├─ lot_utils.py    # normalization logic for lot IDs
│     ├─ models.py       # SQLAlchemy ORM classes
│     ├─ repository.py   # low‑level DB queries
│     └─ services.py     # business logic (satisfies ACs)
├─ tests/                # pytest test suite (covers all ACs)
└─ docs/                 # design documentation (existing)
```

## Getting started

### 1. Install prerequisites

1. [Install Poetry](https://python-poetry.org/docs/).  Make sure Python 3.10+
   is available.
2. Clone the repository and `cd` into the project root.
3. Run:

    ```powershell
    poetry install
    ```

### 2. Configure the environment

By default the application uses an **in-memory SQLite database**.  To point at
another database (e.g. PostgreSQL), supply a `DATABASE_URL` connection string.
The application will automatically load environment variables from a `.env`
file if one is present (see below).

There are two ways to set the variable:

1. **Temporary (current shell)**
    ```powershell
    # Example using the Render PostgreSQL instance you provided:
    $env:DATABASE_URL = \
    "postgresql://steelworks_ops_user:puioXILDnEGUcZD9jUnNr2fvsVPHXXmo@\
    dpg-d6970u1r0fns73fve4sg-a.oregon-postgres.render.com/steelworks_ops"
    ```
2. **Persist via .env file**
    - copy `.env.example` to `.env` **in the project root** (next to `pyproject.toml`), not inside `src/`.
    - edit the `DATABASE_URL` value appropriately, e.g.:

        ```text
        DATABASE_URL=postgresql://steelworks_ops_user:puioXILDnEGUcZD9jUnNr2fvsVPHXXmo@\
        dpg-d6970u1r0fns73fve4sg-a.oregon-postgres.render.com/steelworks_ops
        ```

> ⚠️ The `.env` file must live at the top level of the repository.  The loader
> only searches the working directory and its parents, so placing it inside
> `src/steelworks` (as you currently have) will not work.

Other environment variables you might use in the future can also go in `.env`.

> 🔧 To personalize the project, edit the `authors` field in `pyproject.toml` or
> adjust any of the placeholder metadata there.  There are no external API
> keys required by default.

### 3. Initialize / seed the database

Tables are created automatically when the app starts, but you can also
initialize manually:

```powershell
poetry run python -c "from steelworks import database; database.init_db()"
```

Sample spreadsheet files are located under `data/sample/`.  To import all of
them:

```powershell
poetry run python -c "from steelworks import data_import; data_import.load_all_samples('data/sample')"
```

### 4. Run the application

```powershell
poetry run streamlit run src/steelworks/app.py
```

A browser window will open to the dashboard.  Use the sidebar to set start/end
dates and optionally a production line.  Enter a lot ID in the "Lot Shipping
Status" section to check whether it has shipped.

### 5. Usage examples

- **Filter by date** – pick 2023‑01‑01 through 2023‑01‑07; the "Defects by
  Production Line" table updates accordingly.
- **View trends** – the line chart shows weekly counts for each defect type.
- **Look up a lot** – enter `lot-100` or `LOT 100`; the normalization logic
  ensures both map to the same record (AC6).

### 6. Run tests

The test suite exercises all acceptance criteria.

```powershell
poetry run pytest --cov
```

| Test file              | ACs covered                                    |
|------------------------|------------------------------------------------|
| `tests/test_services.py` | AC1, AC2, AC3, AC4, AC5, AC6                |

(Every AC is covered by at least one test.)


## ✏️ Next steps / customization

To complete or personalize the project, consider editing:

- **`pyproject.toml`** – author names, project description, version, dependencies.
- **`src/steelworks/app.py`** – change UI text, add new features.
- **`src/steelworks/lot_utils.py`** – adjust normalization rules for your data.
- **Environment variables** – notably `DATABASE_URL` for production databases.

No external API keys or secret tokens are required by the current codebase.

---

## 📚 Additional information

Refer to the `docs/` folder for architecture decision records, assumptions,
scope, and data design diagrams.

---

Happy hacking! 👷‍♂️👷‍♀️
