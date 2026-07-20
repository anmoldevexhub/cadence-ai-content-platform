import sqlite3
import json

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

try:
    cursor.execute("SELECT id, title, tags FROM content_contentdraft")
    for row in cursor.fetchall():
        draft_id, title, tags_json = row
        if tags_json:
            try:
                tags = json.loads(tags_json)
                if any(":" in t or "appointment" in t.lower() for t in tags):
                    print(f"Draft ID: {draft_id} | Title: {title}")
                    print("  Tags:", tags)
            except Exception as e:
                pass
except Exception as e:
    print("Error querying database:", e)
finally:
    conn.close()
