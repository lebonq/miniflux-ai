import sqlite3

def insert_if_not_exists(id, datetime, title, summary):
    # Check if the entry already exists
    cursor.execute('SELECT 1 FROM articles WHERE id = ?', (id,))
    exists = cursor.fetchone()

    if not exists:
        # Insert the new entry
        cursor.execute('''
            INSERT INTO articles (id, datetime, title, summary) VALUES (?, ?, ?, ?)
        ''', (id, datetime, title, summary))
        conn.commit()
        print(f"Inserted entry with id {id}")
    else:
        print(f"Entry with id {id} already exists")