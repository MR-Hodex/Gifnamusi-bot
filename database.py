import sqlite3
import secrets
from pathlib import Path


DATABASE = Path(__file__).with_name("database.db")


def connect():
    return sqlite3.connect(DATABASE)


def create_database():
    connection = connect()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            file_id TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_photo(file_id):
    token = secrets.token_urlsafe(12)

    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO photos (token, file_id) VALUES (?, ?)",
        (token, file_id)
    )

    connection.commit()
    connection.close()

    return token


def get_photo(token):
    connection = connect()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT file_id FROM photos WHERE token = ?",
        (token,)
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return None