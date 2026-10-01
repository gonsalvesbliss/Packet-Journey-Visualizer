import sqlite3
from datetime import datetime

DATABASE_NAME = "packet_journey.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination TEXT NOT NULL,
            resolved_ip TEXT,
            timestamp TEXT NOT NULL,
            total_hops INTEGER,
            average_latency REAL,
            packet_loss REAL,
            min_latency REAL,
            max_latency REAL
        )
    """)

    connection.commit()
    connection.close()


def save_trace(result):
    statistics = result["statistics"]

    connection = get_connection()

    connection.execute("""
        INSERT INTO traces (
            destination,
            resolved_ip,
            timestamp,
            total_hops,
            average_latency,
            packet_loss,
            min_latency,
            max_latency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["destination"],
        result["resolved_ip"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        statistics["total_hops"],
        statistics["average_latency"],
        statistics["packet_loss"],
        statistics["min_latency"],
        statistics["max_latency"]
    ))

    connection.commit()
    connection.close()


def get_history():
    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM traces
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return [dict(row) for row in rows]