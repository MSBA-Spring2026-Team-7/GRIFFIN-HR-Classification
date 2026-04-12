"""
cloud_sql_config.py — GCP Cloud SQL connection utility with graceful degradation.

Attempts Cloud SQL (mysql+pymysql) if environment variables are configured,
then falls back to local SQLite so the pipeline always runs.

Usage:
    from cloud_sql_config import get_engine, deploy_schema, verify_schema

    engine = get_engine()          # Cloud SQL if available, else local SQLite
    deploy_schema(engine)          # Load wm_hr_classification_schema.sql
    verify_schema(engine)          # Confirm expected tables exist

Environment variables (set in .env, loaded by python-dotenv):
    CLOUD_SQL_HOST      Public IP of Cloud SQL instance
    CLOUD_SQL_PORT      Port (default 3306)
    CLOUD_SQL_DB        Database name (default griffin_db)
    CLOUD_SQL_USER      Database user
    CLOUD_SQL_PASSWORD  Database password
"""

import os
import ssl
import logging
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text, inspect

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent          # HR_Classification_Project/
_SCHEMA_PATH = _PROJECT_ROOT / "data" / "schema" / "wm_hr_classification_schema.sql"
_LOCAL_DB_PATH = _PROJECT_ROOT / "data" / "griffin_local.db"

# ---------------------------------------------------------------------------
# Expected tables from wm_hr_classification_schema.sql (9 tables)
# ---------------------------------------------------------------------------
EXPECTED_TABLES = [
    "career_groups",
    "roles",
    "historical_titles",
    "soc_codes",
    "dhrm_pay_bands",
    "university_positions",
    "classification_results",
    "classification_confidence_scores",
    "classification_audit_log",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cloud_sql_configured() -> bool:
    """Return True if the minimum Cloud SQL env vars are present."""
    return bool(os.getenv("CLOUD_SQL_HOST") and os.getenv("CLOUD_SQL_PASSWORD"))


def _build_cloud_engine():
    """
    Build a Cloud SQL engine using the class-guide pattern:
        mysql+pymysql  +  SSL context  +  env-var credentials.
    """
    hostname = os.getenv("CLOUD_SQL_HOST")
    port = int(os.getenv("CLOUD_SQL_PORT", "3306"))
    dbname = os.getenv("CLOUD_SQL_DB", "griffin_db")
    username = os.getenv("CLOUD_SQL_USER", "root")
    db_pwd = os.getenv("CLOUD_SQL_PASSWORD")

    conn_string = (
        f"mysql+pymysql://{username}:{quote_plus(db_pwd)}"
        f"@{hostname}:{port}/{dbname}"
    )

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    engine = create_engine(
        conn_string,
        connect_args={"ssl": ssl_context},
        pool_pre_ping=True,
    )
    return engine


def _build_local_engine():
    """Return a SQLite engine pointing at the local project database file."""
    _LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{_LOCAL_DB_PATH}")
    logger.info("Using local SQLite database at %s", _LOCAL_DB_PATH)
    return engine


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_engine():
    """
    Obtain a SQLAlchemy engine.

    Strategy:
        1. If Cloud SQL env vars are set, attempt a live connection.
        2. On any failure (network, auth, missing driver), fall back to local SQLite.
        3. If env vars are absent, go straight to local SQLite.

    Returns:
        sqlalchemy.engine.Engine
    """
    if _cloud_sql_configured():
        try:
            engine = _build_cloud_engine()
            # Test the connection before returning
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to Cloud SQL successfully.")
            return engine
        except Exception as exc:
            logger.warning(
                "Cloud SQL unavailable (%s). Falling back to local SQLite.",
                exc,
            )
    else:
        logger.info("Cloud SQL not configured. Using local SQLite.")

    return _build_local_engine()


def deploy_schema(engine) -> bool:
    """
    Execute the SQL schema file against the given engine.

    For Cloud SQL (MySQL) the file is executed as-is.
    For SQLite the MySQL-specific syntax is stripped so the core
    CREATE TABLE statements still run.

    Returns:
        True if schema was deployed without errors, False otherwise.
    """
    if not _SCHEMA_PATH.exists():
        logger.error("Schema file not found: %s", _SCHEMA_PATH)
        return False

    raw_sql = _SCHEMA_PATH.read_text(encoding="utf-8")

    dialect = engine.dialect.name  # "mysql" or "sqlite"

    if dialect == "sqlite":
        # Strip MySQL-specific syntax for SQLite compatibility
        lines = raw_sql.splitlines()
        cleaned = []
        for line in lines:
            stripped = line.strip().upper()
            # Skip MySQL-only statements
            if stripped.startswith("CREATE DATABASE") or stripped.startswith("USE "):
                continue
            cleaned.append(line)
        raw_sql = "\n".join(cleaned)
        # Remove ENGINE=, DEFAULT CHARSET=, COMMENT= clauses
        import re
        raw_sql = re.sub(r"\)\s*ENGINE=.*?;", ");", raw_sql, flags=re.DOTALL)
        raw_sql = re.sub(r"COMMENT\s*=?\s*'[^']*'", "", raw_sql)
        raw_sql = re.sub(r"DEFAULT\s+CURRENT_TIMESTAMP\s+ON\s+UPDATE\s+CURRENT_TIMESTAMP",
                         "DEFAULT CURRENT_TIMESTAMP", raw_sql)
        raw_sql = re.sub(r"AUTO_INCREMENT", "AUTOINCREMENT", raw_sql)

    try:
        with engine.begin() as conn:
            for statement in raw_sql.split(";"):
                stmt = statement.strip()
                if stmt and not stmt.startswith("--"):
                    conn.execute(text(stmt))
        logger.info("Schema deployed successfully (%s dialect).", dialect)
        return True
    except Exception as exc:
        logger.error("Schema deployment failed: %s", exc)
        return False


def verify_schema(engine) -> dict:
    """
    Check which expected tables exist in the database.

    Returns:
        dict with keys:
            - 'present': list of table names found
            - 'missing': list of table names not found
            - 'all_present': bool
    """
    try:
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
    except Exception as exc:
        logger.error("Schema verification failed: %s", exc)
        return {"present": [], "missing": EXPECTED_TABLES[:], "all_present": False}

    present = [t for t in EXPECTED_TABLES if t in existing]
    missing = [t for t in EXPECTED_TABLES if t not in existing]

    return {
        "present": present,
        "missing": missing,
        "all_present": len(missing) == 0,
    }


# ---------------------------------------------------------------------------
# Quick self-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("cloud_sql_config.py — self-test")
    print("=" * 60)

    eng = get_engine()
    print(f"\nEngine dialect : {eng.dialect.name}")
    print(f"Engine URL     : {eng.url}\n")

    result = verify_schema(eng)
    print(f"Tables present : {len(result['present'])}")
    print(f"Tables missing : {len(result['missing'])}")
    if result["missing"]:
        print(f"  Missing: {result['missing']}")

    print("\nDone.")
