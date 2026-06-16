from sqlalchemy import inspect, text

from app.database import engine


MIGRATIONS = [
    "ALTER TABLE apartment_listings ADD COLUMN title VARCHAR(500)",
    "ALTER TABLE apartment_listings ADD COLUMN compatibility_score INTEGER",
    "ALTER TABLE apartment_listings ADD COLUMN analysis JSON",
    "ALTER TABLE apartment_listings ADD COLUMN parsed_at DATETIME",
    "ALTER TABLE apartment_listings ADD COLUMN photos JSON",
    "ALTER TABLE apartment_listings ADD COLUMN source_site VARCHAR(50)",
    "ALTER TABLE apartment_listings ADD COLUMN landlord_contact JSON",
]


def run_migrations() -> None:
    inspector = inspect(engine)
    if "apartment_listings" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("apartment_listings")}

    with engine.begin() as conn:
        for statement in MIGRATIONS:
            column_name = statement.split("ADD COLUMN ")[1].split()[0]
            if column_name not in existing:
                try:
                    conn.execute(text(statement))
                except Exception:
                    pass
