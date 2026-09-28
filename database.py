import sqlite3
import secrets

def connect():
    return sqlite3.connect("/data/database.db")

def create_database():
    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        file_id TEXT NOT NULL,
        file_type TEXT NOT NULL DEFAULT 'photo'
    )
    """)

    connection.commit()
    connection.close()

def save_photo(file_id, file_type):
    token = secrets.token_urlsafe(12)

    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO photos (token, file_id, file_type) VALUES (?, ?, ?)",
        (token, file_id, file_type)
    )

    connection.commit()
    connection.close()

    return token

def get_photo(token):
    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT file_type, file_id FROM photos WHERE token = ?",
        (token,)
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return result

    return None
