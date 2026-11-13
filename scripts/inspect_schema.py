
import sqlite3

db_path = "data/generated/starter/traceforge.db"

connection = sqlite3.connect(db_path)

query = """
SELECT name, sql
FROM sqlite_master
WHERE type = 'table'
AND name NOT LIKE 'sqlite_%'
ORDER BY name;
"""

tables = connection.execute(query).fetchall()

for table_name, table_sql in tables:
    print("\n" + "=" * 70)
    print(f"TABLE: {table_name}")
    print("=" * 70)
    print(table_sql)

connection.close()
