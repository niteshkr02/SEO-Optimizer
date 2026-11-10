"""Database migration runner for SEO Optimizer PostgreSQL / Supabase databases.

Safely parses SQL statements respecting dollar-quoted strings ($$ ... $$) and comments,
executes migrations statement-by-statement, and tracks migration history in supabase_migrations.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Search for .env
for parent in Path(__file__).resolve().parents:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        break


def get_db_url() -> str:
    db_url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: Neither DIRECT_URL nor DATABASE_URL is configured in environment.")
        sys.exit(1)
    return db_url


def get_supabase_bin() -> str:
    supabase_bin = shutil.which("supabase")
    if not supabase_bin:
        print("ERROR: 'supabase' CLI not found on PATH.")
        sys.exit(1)
    return supabase_bin


def run_sql_query(sql: str) -> tuple[int, str, str]:
    """Executes a single SQL statement using supabase db query via temporary file."""
    supabase_bin = get_supabase_bin()
    db_url = get_db_url()
    
    # Write SQL to temporary file to avoid shell quoting and escaping issues
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False, encoding="utf-8") as f:
        f.write(sql)
        tmp_path = f.name

    try:
        res = subprocess.run(
            [supabase_bin, "db", "query", "--db-url", db_url, "-f", tmp_path],
            check=False,
            capture_output=True,
            text=True,
            shell=True,
        )
        if res.returncode != 0 and "Connection terminated" in (res.stdout + res.stderr):
            time.sleep(1.0)
            res = subprocess.run(
                [supabase_bin, "db", "query", "--db-url", db_url, "-f", tmp_path],
                check=False,
                capture_output=True,
                text=True,
                shell=True,
            )
        return res.returncode, res.stdout, res.stderr
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def split_sql_statements(sql_text: str) -> list[str]:
    """Splits SQL script into individual executable statements respecting dollar quoting and comments."""
    statements: list[str] = []
    current: list[str] = []
    in_dollar: bool = False
    dollar_tag = ""
    in_line_comment: bool = False
    in_block_comment: bool = False
    i = 0
    n = len(sql_text)

    while i < n:
        # Check single-line comment
        if not in_dollar and not in_block_comment and not in_line_comment and sql_text[i : i + 2] == "--":
            in_line_comment = True
            i += 2
            continue
        if in_line_comment:
            if sql_text[i] == "\n":
                in_line_comment = False
            i += 1
            continue

        # Check block comment
        if not in_dollar and not in_line_comment and not in_block_comment and sql_text[i : i + 2] == "/*":
            in_block_comment = True
            i += 2
            continue
        if in_block_comment:
            if sql_text[i : i + 2] == "*/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        # Check dollar quote start or end ($$ or $tag$)
        if not in_dollar and sql_text[i] == "$":
            # Search for closing $ of the tag
            end_tag = sql_text.find("$", i + 1)
            if end_tag != -1:
                tag = sql_text[i : end_tag + 1]
                # Validate tag characters
                tag_content = tag[1:-1]
                if all(c.isalnum() or c == "_" for c in tag_content):
                    in_dollar = True
                    dollar_tag = tag
                    current.append(tag)
                    i = end_tag + 1
                    continue
        elif in_dollar and sql_text[i : i + len(dollar_tag)] == dollar_tag:
            current.append(dollar_tag)
            i += len(dollar_tag)
            in_dollar = False
            dollar_tag = ""
            continue

        # Semicolon outside dollar quote terminates statement
        if sql_text[i] == ";" and not in_dollar:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(sql_text[i])
        i += 1

    remaining = "".join(current).strip()
    if remaining:
        statements.append(remaining)

    return statements


def ensure_migration_table():
    """Ensures supabase_migrations.schema_migrations exists and baseline 001 is recorded."""
    create_schema_sql = "CREATE SCHEMA IF NOT EXISTS supabase_migrations;"
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS supabase_migrations.schema_migrations (
        version VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    for sql in [create_schema_sql, create_table_sql]:
        code, out, err = run_sql_query(sql)
        if code != 0:
            print(f"Failed to ensure migration table: {err}")
            sys.exit(1)

    # If public.leads already exists from 001, ensure 001 is recorded in history
    check_leads_sql = "SELECT 1 AS has_leads FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads';"
    code, out, _ = run_sql_query(check_leads_sql)
    if code == 0:
        try:
            data = json.loads(out)
            if data.get("rows"):
                check_ver = "SELECT 1 FROM supabase_migrations.schema_migrations WHERE version = '001';"
                c2, o2, _ = run_sql_query(check_ver)
                data2 = json.loads(o2) if c2 == 0 else {}
                if not data2.get("rows"):
                    record_migration("001", "001_leads_and_status_history.sql")
        except json.JSONDecodeError:
            pass


def get_applied_migrations() -> list[str]:
    ensure_migration_table()
    code, out, _err = run_sql_query(
        "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version ASC;"
    )
    if code != 0:
        return []
    try:
        data = json.loads(out)
        return [r["version"] for r in data.get("rows", [])]
    except json.JSONDecodeError:
        return []


def record_migration(version: str, name: str):
    sql = f"""
    INSERT INTO supabase_migrations.schema_migrations (version, name, applied_at)
    VALUES ('{version}', '{name}', NOW())
    ON CONFLICT (version) DO UPDATE SET applied_at = NOW();
    """
    code, _out, err = run_sql_query(sql)
    if code != 0:
        print(f"Warning: Failed to record migration {version}: {err}")


def remove_migration(version: str):
    sql = f"DELETE FROM supabase_migrations.schema_migrations WHERE version = '{version}';"
    run_sql_query(sql)


def cmd_status():
    applied = get_applied_migrations()
    print("=== Supabase Staging Migration Status ===")
    print(f"Applied migrations count: {len(applied)}")
    for m in applied:
        print(f"  [APPLIED] {m}")

    migrations_dir = Path(__file__).parent
    files = sorted(migrations_dir.glob("00*.sql"))
    for f in files:
        ver = f.stem.split("_")[0]
        if ver not in applied:
            print(f"  [PENDING] {f.name}")


def cmd_apply(migration_file: str):
    path = Path(migration_file)
    if not path.exists():
        path = Path(__file__).parent / migration_file
    if not path.exists():
        print(f"ERROR: Migration file {migration_file} not found.")
        sys.exit(1)

    version = path.stem.split("_")[0]
    applied = get_applied_migrations()
    if version in applied:
        print(f"Migration {version} is already applied according to schema_migrations.")
        return

    print(f"Applying migration: {path.name}...")
    sql_text = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    print(f"Parsed {len(statements)} statements.")

    for idx, stmt in enumerate(statements, 1):
        code, out, err = run_sql_query(stmt)
        if code != 0:
            print(f"ERROR executing statement {idx}/{len(statements)}:\n{stmt}\nError: {err or out}")
            sys.exit(1)
        first_line = next(l.strip() for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--"))
        print(f"  [{idx}/{len(statements)}] OK: {first_line[:60]}...")

    record_migration(version, path.name)
    print(f"SUCCESS: Migration {path.name} applied successfully and recorded in supabase_migrations.")


def cmd_rollback(rollback_file: str):
    path = Path(rollback_file)
    if not path.exists():
        path = Path(__file__).parent / rollback_file
    if not path.exists():
        print(f"ERROR: Rollback file {rollback_file} not found.")
        sys.exit(1)

    version = path.stem.split("_")[0]
    print(f"Rolling back migration: {path.name}...")
    sql_text = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    print(f"Parsed {len(statements)} rollback statements.")

    for idx, stmt in enumerate(statements, 1):
        code, out, err = run_sql_query(stmt)
        if code != 0:
            print(f"ERROR executing rollback statement {idx}/{len(statements)}:\n{stmt}\nError: {err or out}")
            sys.exit(1)
        first_line = next(l.strip() for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--"))
        print(f"  [{idx}/{len(statements)}] OK: {first_line[:60]}...")

    remove_migration(version)
    print(f"SUCCESS: Migration {version} rolled back successfully.")


def cmd_test(test_file: str):
    path = Path(test_file)
    if not path.exists():
        path = Path(__file__).parent / "tests" / test_file
    if not path.exists():
        print(f"ERROR: Test file {test_file} not found.")
        sys.exit(1)

    print(f"Running SQL verification test: {path.name}...")
    sql_text = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    print(f"Executing {len(statements)} statement(s)...")

    for idx, stmt in enumerate(statements, 1):
        code, out, err = run_sql_query(stmt)
        if code != 0:
            print(f"TEST FAILED at statement {idx}:\n{stmt}\nError: {err or out}")
            sys.exit(1)
        print(f"  Statement {idx} executed cleanly. Output:\n{out.strip()}")

    print(f"SUCCESS: All tests in {path.name} passed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEO Optimizer Supabase Migration Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show migration status")

    apply_parser = subparsers.add_parser("apply", help="Apply a migration")
    apply_parser.add_argument("file", help="Migration file name (e.g. 002_atomic_rate_limiting_and_anon_hardening.sql)")

    rollback_parser = subparsers.add_parser("rollback", help="Roll back a migration")
    rollback_parser.add_argument("file", help="Rollback file name (e.g. 002_rollback.sql)")

    test_parser = subparsers.add_parser("test", help="Run a test SQL file")
    test_parser.add_argument("file", help="Test SQL file name (e.g. test_migration_002_hardening.sql)")

    args = parser.parse_args()
    if args.command == "status":
        cmd_status()
    elif args.command == "apply":
        cmd_apply(args.file)
    elif args.command == "rollback":
        cmd_rollback(args.file)
    elif args.command == "test":
        cmd_test(args.file)
