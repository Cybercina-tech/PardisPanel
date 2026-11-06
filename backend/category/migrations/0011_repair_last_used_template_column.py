"""
Repair DBs where django_migrations shows 0010 applied but the SQLite/Postgres
table never received ``last_used_template_id`` (avoids OperationalError on any
query touching Category).
"""

from django.db import migrations


def _column_exists(schema_editor, table: str, column: str) -> bool:
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            # PRAGMA expects the bare table name (not quoted identifiers).
            cursor.execute(f"PRAGMA table_info({table})")
            return any(row[1] == column for row in cursor.fetchall())
        if connection.vendor == "postgresql":
            cursor.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                """,
                [table, column],
            )
            return cursor.fetchone() is not None
    return False


def repair_last_used_template_column(apps, schema_editor):
    table = "category_category"
    column = "last_used_template_id"
    if _column_exists(schema_editor, table, column):
        return

    connection = schema_editor.connection
    quoted_table = connection.ops.quote_name(table)
    quoted_tpl = connection.ops.quote_name("template_editor_template")
    quoted_col = connection.ops.quote_name(column)

    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            # INTEGER NULL FK — SQLite stores BIGINT as INTEGER.
            cursor.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_col} "
                f"INTEGER NULL REFERENCES {quoted_tpl} (id) ON DELETE SET NULL"
            )
        elif connection.vendor == "postgresql":
            cursor.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_col} bigint NULL"
            )
            cursor.execute(
                f"""
                ALTER TABLE {quoted_table}
                ADD CONSTRAINT category_category_last_used_template_repair_fkey
                FOREIGN KEY ({quoted_col})
                REFERENCES {quoted_tpl}(id)
                ON DELETE SET NULL
                """
            )
        else:
            # Other backends: rely on standard migrate path; no-op here.
            return


class Migration(migrations.Migration):

    dependencies = [
        ("category", "0010_category_last_used_template"),
        ("template_editor", "0007_template_publish_telegram_fields"),
    ]

    operations = [
        migrations.RunPython(repair_last_used_template_column, migrations.RunPython.noop),
    ]
