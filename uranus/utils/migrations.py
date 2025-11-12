"""
Project-wide migration utilities for PostgreSQL
Provides helpers for loading SQL files and checking database state
Can be used across all Django apps in the project
"""

from pathlib import Path
from django.db import connection


def load_sql_from_app(migration_file, sql_filename):
    """
    Load SQL file from any app's sql directory

    Args:
        migration_file: Pass __file__ from the migration
        sql_filename: Relative path from sql/ directory (e.g., 'functions/my_func.sql')

    Returns:
        str: Content of the SQL file

    Example:
        from your_project.utils.migrations import load_sql_from_app

        operations = [
            migrations.RunSQL(
                sql=load_sql_from_app(__file__, 'functions/calculate_discount.sql'),
                reverse_sql="DROP FUNCTION IF EXISTS calculate_discount();"
            ),
        ]

    Raises:
        FileNotFoundError: If the SQL file doesn't exist
    """
    migration_dir = Path(migration_file).parent
    app_dir = migration_dir.parent
    sql_path = app_dir / "sql" / sql_filename

    if not sql_path.exists():
        raise FileNotFoundError(
            f"SQL file not found: {sql_path}\n"
            f"Expected location: {app_dir}/sql/{sql_filename}\n"
            f"Make sure the file exists and the path is correct."
        )

    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    return content.strip()


def load_sql_pair(migration_file, forward_file, reverse_file):
    """
    Load both forward and reverse SQL files

    Args:
        migration_file: Pass __file__ from the migration
        forward_file: Path to forward SQL (e.g., 'functions/my_func.sql')
        reverse_file: Path to reverse SQL (e.g., 'functions/my_func_reverse.sql')

    Returns:
        tuple: (forward_sql, reverse_sql)

    Example:
        forward, reverse = load_sql_pair(
            __file__,
            'functions/calculate_discount.sql',
            'functions/calculate_discount_reverse.sql'
        )

        operations = [
            migrations.RunSQL(sql=forward, reverse_sql=reverse),
        ]
    """
    forward_sql = load_sql_from_app(migration_file, forward_file)
    reverse_sql = load_sql_from_app(migration_file, reverse_file)
    return forward_sql, reverse_sql


def load_sql_with_reverse(migration_file, sql_filename):
    """
    Load SQL file and automatically find reverse file

    Looks for reverse file with naming patterns:
    - functions/my_func.sql → functions/my_func_reverse.sql
    - functions/my_func.sql → functions/my_func_rollback.sql
    - functions/my_func.sql → functions/reverse/my_func.sql

    Args:
        migration_file: Pass __file__ from the migration
        sql_filename: Path to forward SQL

    Returns:
        tuple: (forward_sql, reverse_sql or None)

    Example:
        operations = [
            migrations.RunSQL(*load_sql_with_reverse(__file__, 'functions/my_func.sql')),
        ]
    """
    migration_dir = Path(migration_file).parent
    app_dir = migration_dir.parent

    # Load forward SQL
    forward_path = app_dir / "sql" / sql_filename
    if not forward_path.exists():
        raise FileNotFoundError(f"SQL file not found: {forward_path}")

    with open(forward_path, "r", encoding="utf-8") as f:
        forward_sql = f.read().strip()

    # Try to find reverse SQL with different naming patterns
    sql_path = Path(sql_filename)
    base_name = sql_path.stem  # filename without extension
    parent_dir = sql_path.parent

    # Try multiple patterns
    reverse_patterns = [
        parent_dir / f"{base_name}_reverse.sql",
        parent_dir / f"{base_name}_rollback.sql",
        parent_dir / "reverse" / sql_path.name,
        parent_dir / "rollback" / sql_path.name,
    ]

    reverse_sql = None
    for pattern in reverse_patterns:
        reverse_path = app_dir / "sql" / pattern
        if reverse_path.exists():
            with open(reverse_path, "r", encoding="utf-8") as f:
                reverse_sql = f.read().strip()
            break

    if reverse_sql is None:
        print(f"⚠️  Warning: No reverse SQL found for {sql_filename}")
        print(f"   Tried: {[str(p) for p in reverse_patterns]}")

    return forward_sql, reverse_sql


def function_exists(function_name, schema="public"):
    """
    Check if a PostgreSQL function exists

    Args:
        function_name: Name of the function
        schema: Database schema (default: 'public')

    Returns:
        bool: True if function exists, False otherwise

    Example:
        from your_project.utils.migrations import function_exists

        if function_exists('calculate_discount'):
            print("Function already exists")
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE p.proname = %s AND n.nspname = %s
            )
        """,
            [function_name, schema],
        )
        return cursor.fetchone()[0]


def trigger_exists(trigger_name, table_name=None, schema="public"):
    """
    Check if a PostgreSQL trigger exists

    Args:
        trigger_name: Name of the trigger
        table_name: Optional table name to check specific table
        schema: Database schema (default: 'public')

    Returns:
        bool: True if trigger exists, False otherwise

    Example:
        if trigger_exists('audit_product_changes', 'products'):
            print("Trigger exists on products table")
    """
    with connection.cursor() as cursor:
        if table_name:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_trigger t
                    JOIN pg_class c ON t.tgrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE t.tgname = %s
                    AND c.relname = %s
                    AND n.nspname = %s
                )
            """,
                [trigger_name, table_name, schema],
            )
        else:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_trigger t
                    JOIN pg_class c ON t.tgrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE t.tgname = %s
                    AND n.nspname = %s
                )
            """,
                [trigger_name, schema],
            )
        return cursor.fetchone()[0]


def type_exists(type_name, schema="public"):
    """
    Check if a PostgreSQL custom type exists

    Args:
        type_name: Name of the type
        schema: Database schema (default: 'public')

    Returns:
        bool: True if type exists, False otherwise

    Example:
        if type_exists('address_type'):
            print("Type exists")
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_type t
                JOIN pg_namespace n ON t.typnamespace = n.oid
                WHERE t.typname = %s AND n.nspname = %s
            )
        """,
            [type_name, schema],
        )
        return cursor.fetchone()[0]


def procedure_exists(procedure_name, schema="public"):
    """
    Check if a PostgreSQL procedure exists (PostgreSQL 11+)

    Args:
        procedure_name: Name of the procedure
        schema: Database schema (default: 'public')

    Returns:
        bool: True if procedure exists, False otherwise

    Example:
        if procedure_exists('cleanup_old_data'):
            print("Procedure exists")
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE p.proname = %s
                AND n.nspname = %s
                AND p.prokind = 'p'  -- 'p' for procedure
            )
        """,
            [procedure_name, schema],
        )
        return cursor.fetchone()[0]


def extension_exists(extension_name):
    """
    Check if a PostgreSQL extension is installed

    Args:
        extension_name: Name of the extension

    Returns:
        bool: True if extension is installed, False otherwise

    Example:
        if not extension_exists('uuid-ossp'):
            print("Extension needs to be installed")
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_extension
                WHERE extname = %s
            )
        """,
            [extension_name],
        )
        return cursor.fetchone()[0]


def table_exists(table_name, schema="public"):
    """
    Check if a table exists

    Args:
        table_name: Name of the table
        schema: Database schema (default: 'public')

    Returns:
        bool: True if table exists, False otherwise

    Example:
        if table_exists('audit_log'):
            print("Table exists")
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            )
        """,
            [schema, table_name],
        )
        return cursor.fetchone()[0]


def index_exists(index_name, schema="public"):
    """
    Check if an index exists

    Args:
        index_name: Name of the index
        schema: Database schema (default: 'public')

    Returns:
        bool: True if index exists, False otherwise

    Example:
        if index_exists('idx_email'):
            print("Index exists")
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = %s AND indexname = %s
            )
        """,
            [schema, index_name],
        )
        return cursor.fetchone()[0]


def execute_sql_safely(sql, params=None):
    """
    Execute SQL with proper error handling

    Args:
        sql: SQL statement to execute
        params: Optional parameters for the SQL statement

    Returns:
        Any: Result of the query (if applicable)

    Example:
        result = execute_sql_safely(
            "SELECT * FROM my_function(%s, %s)",
            [arg1, arg2]
        )
    """
    with connection.cursor() as cursor:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        # Try to fetch results if it's a SELECT query
        try:
            return cursor.fetchall()
        except Exception:
            # Not a SELECT query, return None
            return None
