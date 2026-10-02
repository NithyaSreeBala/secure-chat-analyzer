import sqlite3
import os

DB_PATH = os.path.join("instance", "chat_analyzer.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute(
        "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"
    )

    conn.commit()

    print("✅ Role column added successfully!")

except sqlite3.OperationalError as e:

    if "duplicate column name" in str(e).lower():
        print("ℹ️ Role column already exists.")

    else:
        print("❌ Database error:", e)

finally:
    conn.close()