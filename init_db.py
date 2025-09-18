import sqlite3

conn = sqlite3.connect('smartdoc_data.db')
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    analysis_date TEXT NOT NULL
)
''')

conn.commit()
conn.close()

print("Database initialized with history table.")
