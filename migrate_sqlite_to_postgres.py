import json
import os
import sys
from urllib.parse import urlparse
from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.exc import InvalidRequestError, OperationalError
from dotenv import load_dotenv

load_dotenv()

TABLES = ["users", "chat_history", "plant_analysis"]


def normalize_database_url(database_url):
    if not database_url:
        return database_url

    # SQLAlchemy defaults postgresql:// to psycopg2; force psycopg v3 dialect.
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    if database_url.startswith("postgresql+psycopg://"):
        return database_url

    return database_url


def build_sqlite_url(sqlite_url):
    if sqlite_url:
        return sqlite_url
    default_path = os.path.join("instance", "plankton.db")
    return f"sqlite:///{default_path}"


def get_target_url():
    # Optional override to avoid clashing with app runtime DATABASE_URL.
    target = os.getenv("TARGET_DATABASE_URL") or os.getenv("DATABASE_URL")
    return normalize_database_url(target)


def looks_like_placeholder_url(url):
    if not url:
        return False

    parsed = urlparse(url)
    username = (parsed.username or "").strip().lower()
    password = (parsed.password or "").strip().lower()
    host = (parsed.hostname or "").strip().lower()
    database = (parsed.path or "").strip("/").lower()

    # Block only obvious template values from .env.example.
    return (
        username == "username"
        and password == "password"
        and host in {"localhost", "127.0.0.1"}
        and database == "plankton"
    )


def to_json_value(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def reset_postgres_sequence(conn, table_name):
    query = text(
        """
        SELECT setval(
            pg_get_serial_sequence(:table_name, 'id'),
            COALESCE((SELECT MAX(id) FROM """ + table_name + """), 1),
            (SELECT MAX(id) IS NOT NULL FROM """ + table_name + """)
        )
        """
    )
    conn.execute(query, {"table_name": table_name})


def main():
    sqlite_url = build_sqlite_url(os.getenv("SQLITE_DATABASE_URL"))
    target_url = get_target_url()

    if not target_url:
        print("ERROR: DATABASE_URL belum diset. Isi dengan URL PostgreSQL.")
        sys.exit(1)

    if not target_url.startswith("postgresql+psycopg://"):
        print("ERROR: DATABASE_URL harus mengarah ke PostgreSQL.")
        sys.exit(1)

    if looks_like_placeholder_url(target_url):
        print("ERROR: DATABASE_URL/TARGET_DATABASE_URL masih placeholder.")
        print("Isi dengan URL PostgreSQL yang valid, contoh Railway:")
        print("postgresql://<user>:<password>@<host>:<port>/<database>")
        sys.exit(1)

    source_engine = create_engine(sqlite_url)
    target_engine = create_engine(target_url)

    source_meta = MetaData()
    source_meta.reflect(bind=source_engine, only=TABLES)

    target_meta = MetaData()
    try:
        target_meta.reflect(bind=target_engine, only=TABLES)
    except InvalidRequestError:
        print("ERROR: Tabel PostgreSQL belum tersedia (users, chat_history, plant_analysis).")
        print("Jalankan inisialisasi tabel terlebih dulu:")
        print("./myenv/bin/python -c \"from app import create_app; create_app(register_blueprints=False); print('tables initialized')\"")
        sys.exit(1)
    except OperationalError as exc:
        print("ERROR: Gagal konek ke PostgreSQL target.")
        print(f"Detail: {exc}")
        print("Periksa username/password/host/port/database pada DATABASE_URL atau TARGET_DATABASE_URL.")
        sys.exit(1)

    missing_tables = [table for table in TABLES if table not in target_meta.tables]
    if missing_tables:
        print("ERROR: Tabel PostgreSQL belum ada:", ", ".join(missing_tables))
        print("Jalankan aplikasi sekali dengan DATABASE_URL PostgreSQL agar db.create_all() membuat tabel.")
        sys.exit(1)

    with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
        # Clear target tables safely in reverse FK order.
        for table_name in reversed(TABLES):
            target_conn.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))

        for table_name in TABLES:
            source_table = source_meta.tables[table_name]
            target_table = target_meta.tables[table_name]

            rows = source_conn.execute(select(source_table)).mappings().all()
            processed_rows = []

            for row in rows:
                row_dict = dict(row)
                if table_name == "plant_analysis":
                    row_dict["analysis_result"] = to_json_value(row_dict.get("analysis_result"))
                processed_rows.append(row_dict)

            if processed_rows:
                target_conn.execute(target_table.insert(), processed_rows)

            print(f"Migrated {len(processed_rows)} rows from {table_name}")

        for table_name in TABLES:
            reset_postgres_sequence(target_conn, table_name)

    print("Migration completed successfully.")


if __name__ == "__main__":
    main()
