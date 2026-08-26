import os
from collections.abc import Iterator

import dotenv
import mysql.connector
from fastapi import HTTPException

dotenv.load_dotenv()


def get_connection() -> mysql.connector.MySQLConnection:
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
    except mysql.connector.Error as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e.msg}") from e


def get_db() -> Iterator[mysql.connector.MySQLConnection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
