import sqlite3
import os


DATABASE_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "database")
)

DATABASE_PATH = os.path.join(DATABASE_FOLDER, "evidence.db")


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def initialize_database():

    os.makedirs(DATABASE_FOLDER, exist_ok=True)

    connection = get_connection()
    cursor = connection.cursor()

    # Cases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            investigator TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Evidence table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            evidence_type TEXT,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")