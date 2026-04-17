"""
cloud_sql_setup.py -- GCP Cloud SQL Database Setup Utility
==========================================================

Starting point for deploying the GRIFFIN database to Google Cloud SQL.
Run this script to connect to your Cloud SQL instance, deploy the schema,
and verify that all 9 expected tables are present.

This is a user-friendly wrapper around app/cloud_sql_config.py.
An IT officer following the Technical Transition Guide should be able
to run this script to set up or verify the database.

Usage:
    python tools/cloud_sql_setup.py              # Auto-detect: Cloud SQL if configured, else local SQLite
    python tools/cloud_sql_setup.py --local-only  # Force local SQLite (no cloud credentials needed)

Prerequisites:
    pip install sqlalchemy pymysql python-dotenv

Environment variables (set in .env file at project root):
    CLOUD_SQL_HOST      Public IP of your Cloud SQL instance
    CLOUD_SQL_PORT      Port number (default: 3306)
    CLOUD_SQL_DB        Database name (default: griffin_db)
    CLOUD_SQL_USER      Database user (default: root)
    CLOUD_SQL_PASSWORD  Database password
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so we can import from app/
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent          # tools/
_PROJECT_ROOT = _SCRIPT_DIR.parent                      # HR_Classification_Project/
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    _env_path = _PROJECT_ROOT / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv not installed; env vars must be set manually

from app.cloud_sql_config import get_engine, deploy_schema, verify_schema, EXPECTED_TABLES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_header(text: str) -> None:
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def _print_step(step_num: int, text: str) -> None:
    """Print a numbered step."""
    print(f"\n  [{step_num}] {text}")


def _check_cloud_credentials() -> bool:
    """Check if Cloud SQL environment variables are configured."""
    host = os.getenv("CLOUD_SQL_HOST")
    password = os.getenv("CLOUD_SQL_PASSWORD")
    return bool(host and password)


def _print_env_instructions() -> None:
    """Print instructions for setting up Cloud SQL credentials."""
    env_path = _PROJECT_ROOT / ".env"
    print()
    print("  Cloud SQL credentials are NOT configured.")
    print()
    print("  To connect to GCP Cloud SQL, create a .env file at:")
    print(f"    {env_path}")
    print()
    print("  Required variables:")
    print("    CLOUD_SQL_HOST=<your-cloud-sql-public-ip>")
    print("    CLOUD_SQL_PASSWORD=<your-database-password>")
    print()
    print("  Optional variables (have defaults):")
    print("    CLOUD_SQL_PORT=3306")
    print("    CLOUD_SQL_DB=griffin_db")
    print("    CLOUD_SQL_USER=root")
    print()


# ---------------------------------------------------------------------------
# Main setup flow
# ---------------------------------------------------------------------------

def run_setup(local_only: bool = False) -> bool:
    """
    Run the full database setup flow.

    Steps:
        1. Check credentials (or use local SQLite)
        2. Connect to the database
        3. Deploy the schema
        4. Verify all expected tables exist

    Returns:
        True if all steps succeeded, False otherwise.
    """
    _print_header("GRIFFIN Database Setup")

    # ------------------------------------------------------------------
    # Step 1: Determine connection mode
    # ------------------------------------------------------------------
    _print_step(1, "Checking database connection mode...")

    if local_only:
        print("      Mode: LOCAL SQLITE (--local-only flag set)")
        print("      This creates a local database for testing/demo purposes.")
        # Force local by clearing any cloud vars temporarily
        saved_host = os.environ.pop("CLOUD_SQL_HOST", None)
        saved_pass = os.environ.pop("CLOUD_SQL_PASSWORD", None)
    elif _check_cloud_credentials():
        print("      Mode: CLOUD SQL (credentials found)")
        host = os.getenv("CLOUD_SQL_HOST")
        db = os.getenv("CLOUD_SQL_DB", "griffin_db")
        print(f"      Host: {host}")
        print(f"      Database: {db}")
    else:
        print("      Mode: LOCAL SQLITE (no Cloud SQL credentials found)")
        _print_env_instructions()
        print("      Proceeding with local SQLite as a demo...")

    # ------------------------------------------------------------------
    # Step 2: Connect
    # ------------------------------------------------------------------
    _print_step(2, "Connecting to database...")

    try:
        engine = get_engine()
        dialect = engine.dialect.name
        print(f"      Connected successfully.")
        print(f"      Dialect: {dialect}")
        print(f"      URL: {engine.url}")
    except Exception as exc:
        print(f"      FAILED to connect: {exc}")
        if local_only:
            # Restore env vars
            if saved_host:
                os.environ["CLOUD_SQL_HOST"] = saved_host
            if saved_pass:
                os.environ["CLOUD_SQL_PASSWORD"] = saved_pass
        return False

    # ------------------------------------------------------------------
    # Step 3: Deploy schema
    # ------------------------------------------------------------------
    _print_step(3, "Deploying database schema...")

    schema_file = _PROJECT_ROOT / "data" / "schema" / "wm_hr_classification_schema.sql"
    if not schema_file.exists():
        print(f"      FAILED: Schema file not found at:")
        print(f"        {schema_file}")
        return False

    print(f"      Schema file: {schema_file.name}")

    success = deploy_schema(engine)
    if success:
        print("      Schema deployed successfully.")
    else:
        print("      FAILED to deploy schema. Check the log output above.")
        return False

    # ------------------------------------------------------------------
    # Step 4: Verify tables
    # ------------------------------------------------------------------
    _print_step(4, "Verifying database tables...")

    result = verify_schema(engine)

    print(f"      Expected tables: {len(EXPECTED_TABLES)}")
    print(f"      Tables found:    {len(result['present'])}")
    print(f"      Tables missing:  {len(result['missing'])}")

    if result["present"]:
        print()
        print("      Present:")
        for t in result["present"]:
            print(f"        [OK] {t}")

    if result["missing"]:
        print()
        print("      Missing:")
        for t in result["missing"]:
            print(f"        [!!] {t}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _print_header("Setup Summary")

    if result["all_present"]:
        print(f"  SUCCESS: All {len(EXPECTED_TABLES)} tables are present.")
        print(f"  Database is ready for use.")
        if dialect == "sqlite":
            db_path = _PROJECT_ROOT / "data" / "griffin_local.db"
            print(f"\n  Local database location:")
            print(f"    {db_path}")
            print(f"\n  Note: This is a local SQLite database for testing.")
            print(f"  For production, configure Cloud SQL credentials in .env")
        else:
            print(f"\n  Cloud SQL database is configured and verified.")
    else:
        print(f"  PARTIAL: {len(result['present'])} of {len(EXPECTED_TABLES)} tables found.")
        print(f"  Review the missing tables above and check the schema file.")
        return False

    # Restore env vars if we cleared them
    if local_only:
        if saved_host:
            os.environ["CLOUD_SQL_HOST"] = saved_host
        if saved_pass:
            os.environ["CLOUD_SQL_PASSWORD"] = saved_pass

    print()
    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="GRIFFIN Database Setup -- deploy and verify the Cloud SQL schema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/cloud_sql_setup.py              # Auto: Cloud SQL if configured, else SQLite
  python tools/cloud_sql_setup.py --local-only  # Force local SQLite for testing
        """,
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Use local SQLite database only (skip Cloud SQL even if credentials exist)",
    )

    args = parser.parse_args()

    # Configure logging so cloud_sql_config messages are visible
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    success = run_setup(local_only=args.local_only)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
