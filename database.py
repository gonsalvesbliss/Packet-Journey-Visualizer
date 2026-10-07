import sqlite3
from datetime import datetime

DATABASE_NAME = "packet_journey.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    connection = get_connection()

    # Create the table if it does not already exist
    connection.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination TEXT NOT NULL,
            resolved_ip TEXT,
            timestamp TEXT NOT NULL,
            operation TEXT NOT NULL DEFAULT 'traceroute',
            total_hops INTEGER,
            average_latency REAL,
            packet_loss REAL,
            min_latency REAL,
            max_latency REAL
        )
    """)

    # --------------------------------------------------
    # BACKWARD COMPATIBILITY
    # --------------------------------------------------
    # If the database was created using the old schema,
    # add the new operation column without deleting data.

    columns = connection.execute("""
        PRAGMA table_info(traces)
    """).fetchall()

    column_names = [column["name"] for column in columns]

    if "operation" not in column_names:

        connection.execute("""
            ALTER TABLE traces
            ADD COLUMN operation TEXT NOT NULL DEFAULT 'traceroute'
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
            operation,
            total_hops,
            average_latency,
            packet_loss,
            min_latency,
            max_latency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["destination"],
        result["resolved_ip"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        result.get("operation", "traceroute"),
        statistics.get("total_hops"),
        statistics.get("average_latency"),
        statistics.get("packet_loss"),
        statistics.get("min_latency"),
        statistics.get("max_latency")
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