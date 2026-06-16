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
    "ALTER TABLE apartment_listings ADD COLUMN is_favorite BOOLEAN DEFAULT 0",
    "ALTER TABLE student_profiles ADD COLUMN user_id INTEGER",
]


def run_migrations() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "apartment_listings" in table_names:
        existing = {col["name"] for col in inspector.get_columns("apartment_listings")}
        with engine.begin() as conn:
            for statement in MIGRATIONS:
                if "apartment_listings" not in statement:
                    continue
                column_name = statement.split("ADD COLUMN ")[1].split()[0]
                if column_name not in existing:
                    try:
                        conn.execute(text(statement))
                    except Exception:
                        pass

    if "student_profiles" in table_names:
        existing = {col["name"] for col in inspector.get_columns("student_profiles")}
        with engine.begin() as conn:
            for statement in MIGRATIONS:
                if "student_profiles" not in statement:
                    continue
                column_name = statement.split("ADD COLUMN ")[1].split()[0]
                if column_name not in existing:
                    try:
                        conn.execute(text(statement))
                    except Exception:
                        pass
