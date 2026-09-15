#!/usr/bin/env python3
import argparse
import os
import json
from typing import List

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values, Json
from decouple import Config, RepositoryEnv


def load_config(base_dir: str) -> Config:
    env_path = os.path.join(base_dir, ".env")
    return Config(RepositoryEnv(env_path))


def connect_db(host: str, port: str, user: str, password: str, dbname: str):
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
    )


def get_tables(cursor) -> List[str]:
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
          AND table_name <> 'django_migrations'
        ORDER BY table_name
        """
    )
    return [row[0] for row in cursor.fetchall()]


def get_columns(cursor, table: str) -> List[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [row[0] for row in cursor.fetchall()]


def reset_sequences(cursor):
    cursor.execute(
        """
        SELECT c.table_name, c.column_name,
               pg_get_serial_sequence(format('%I.%I', 'public', c.table_name), c.column_name) AS seq_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.column_default LIKE 'nextval(%'
        """
    )
    rows = cursor.fetchall()
    for table_name, column_name, seq_name in rows:
        if not seq_name:
            continue
        cursor.execute(
            sql.SQL("SELECT COALESCE(MAX({}), 0) + 1 FROM {}.{}").format(
                sql.Identifier(column_name),
                sql.Identifier("public"),
                sql.Identifier(table_name),
            )
        )
        next_val = int(cursor.fetchone()[0])
        cursor.execute("SELECT setval(%s, %s, false)", (seq_name, next_val))


def write_status(status_file: str | None, state: str, progress: int, message: str):
    if not status_file:
        return
    payload = {
        "state": state,
        "progress": max(0, min(100, int(progress))),
        "message": message,
    }
    with open(status_file, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def print_progress(done: int, total: int, label: str):
    total = max(total, 1)
    pct = int((done / total) * 100)
    width = 28
    fill = int((pct / 100) * width)
    bar = "#" * fill + "-" * (width - fill)
    print(f"\r[{bar}] {pct:3d}% {label}", end="", flush=True)


def adapt_row(row):
    converted = []
    for value in row:
        if isinstance(value, (dict, list)):
            converted.append(Json(value))
        else:
            converted.append(value)
    return tuple(converted)


def main():
    parser = argparse.ArgumentParser(description="Force sync local DB data into remote DB")
    parser.add_argument("--dry-run", action="store_true", help="Check connectivity only")
    parser.add_argument("--status-file", default="", help="Path to JSON status file")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg = load_config(base_dir)

    remote = {
        "host": cfg("REMOTE_DATABASE_HOST", default="localhost"),
        "port": cfg("REMOTE_DATABASE_PORT", default="5432"),
        "user": cfg("REMOTE_DATABASE_USER", default="postgres"),
        "password": cfg("REMOTE_DATABASE_PASS", default=""),
        "dbname": cfg("REMOTE_DATABASE_NAME", default="commerce_expert"),
    }
    local = {
        "host": cfg("LOCAL_DATABASE_HOST", default="localhost"),
        "port": cfg("LOCAL_DATABASE_PORT", default="5432"),
        "user": cfg("LOCAL_DATABASE_USER", default="postgres"),
        "password": cfg("LOCAL_DATABASE_PASS", default=""),
        "dbname": cfg("LOCAL_DATABASE_NAME", default="commerce_expert"),
    }

    remote_conn = connect_db(**remote)
    local_conn = connect_db(**local)
    remote_conn.autocommit = False
    local_conn.autocommit = False

    try:
        status_file = args.status_file or None
        write_status(status_file, "running", 0, "Connecting to databases")

        with local_conn.cursor() as local_cur, remote_conn.cursor() as remote_cur:
            local_cur.execute("SELECT 1")
            remote_cur.execute("SELECT 1")

            if args.dry_run:
                write_status(status_file, "completed", 100, "Connectivity check OK")
                print("Local/remote connectivity OK")
                local_conn.rollback()
                remote_conn.rollback()
                return

            tables = get_tables(local_cur)
            if not tables:
                write_status(status_file, "completed", 100, "No local tables found")
                print("No tables found on local")
                local_conn.rollback()
                remote_conn.rollback()
                return

            total_rows = 0
            for table in tables:
                local_cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier("public"), sql.Identifier(table)))
                total_rows += int(local_cur.fetchone()[0])

            write_status(status_file, "running", 2, f"Preparing remote reset for {len(tables)} tables")

            truncate_stmt = sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(
                    [sql.Identifier("public", table) for table in tables]
                )
            )
            remote_cur.execute(truncate_stmt)

            copied_rows = 0
            print_progress(0, max(total_rows, 1), "Starting copy")

            for table in tables:
                local_cols = get_columns(local_cur, table)
                remote_cols = get_columns(remote_cur, table)
                common_cols = [col for col in local_cols if col in remote_cols]
                if not common_cols:
                    continue

                select_stmt = sql.SQL("SELECT {} FROM {}.{}").format(
                    sql.SQL(", ").join([sql.Identifier(col) for col in common_cols]),
                    sql.Identifier("public"),
                    sql.Identifier(table),
                )
                local_cur.execute(select_stmt)

                insert_stmt = sql.SQL("INSERT INTO {}.{} ({}) VALUES %s").format(
                    sql.Identifier("public"),
                    sql.Identifier(table),
                    sql.SQL(", ").join([sql.Identifier(col) for col in common_cols]),
                )

                while True:
                    rows = local_cur.fetchmany(1000)
                    if not rows:
                        break
                    prepared_rows = [adapt_row(row) for row in rows]
                    execute_values(remote_cur, insert_stmt.as_string(remote_conn), prepared_rows, page_size=1000)
                    copied_rows += len(rows)
                    print_progress(copied_rows, max(total_rows, 1), f"Copying {table}")
                    pct = int((copied_rows / max(total_rows, 1)) * 95)
                    write_status(status_file, "running", pct, f"Copying {table}: {copied_rows}/{total_rows}")

            reset_sequences(remote_cur)
            remote_conn.commit()
            local_conn.rollback()
            print()
            write_status(status_file, "completed", 100, "Local data force-synced into remote database")
            print("Local data force-synced into remote database")

    except Exception:
        remote_conn.rollback()
        local_conn.rollback()
        write_status(args.status_file or None, "failed", 100, "Local-to-remote sync failed")
        print()
        raise
    finally:
        remote_conn.close()
        local_conn.close()


if __name__ == "__main__":
    main()
