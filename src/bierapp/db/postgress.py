"""PostgreSQL Database Repository - Low-level database access layer."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor


class PostgresRepository:
    """Repository handling PostgreSQL database operations."""

    def __init__(self):
        """Initialize the PostgreSQL repository."""
        self.conn = None

    def connect(self):
        """Establish a connection to the PostgreSQL database if none exists.

        Raises:
            psycopg2.Error: If database connection fails.
        """
        if self.conn is None:
            self.conn = psycopg2.connect(host=os.environ.get("POSTGRES_HOST", "localhost"), port=int(os.environ.get("POSTGRES_PORT", 5432)), database=os.environ.get("POSTGRES_DB", "lagerverwaltung"), user=os.environ.get("POSTGRES_USER", "admin"), password=os.environ.get("POSTGRES_PASSWORD", "secret"))
            self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create required application tables when they do not yet exist.

        Raises:
            psycopg2.Error: If schema initialization fails.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS products (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        beschreibung TEXT DEFAULT '',
                        gewicht DOUBLE PRECISION NOT NULL CHECK (gewicht > 0)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS warehouses (
                        id SERIAL PRIMARY KEY,
                        lagername TEXT NOT NULL,
                        adresse TEXT NOT NULL,
                        max_plaetze INTEGER NOT NULL CHECK (max_plaetze > 0),
                        firma_id INTEGER NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS inventory (
                        id SERIAL PRIMARY KEY,
                        lager_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
                        produkt_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                        menge INTEGER NOT NULL CHECK (menge > 0),
                        UNIQUE (lager_id, produkt_id)
                    )
                    """
                )

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS history (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        entry_type TEXT NOT NULL,
                        action TEXT NOT NULL,
                        details TEXT NOT NULL DEFAULT ''
                    )
                    """
                )
            self.conn.commit()
        except psycopg2.Error:
            self.conn.rollback()
            raise

    def insert(self, table: str, data: dict) -> str:
        """Insert a new record into the specified table.

        Args:
            table (str): The name of the database table.
            data (dict): A dictionary containing column names and values.

        Returns:
            str: The ID of the newly inserted record.
        """
        try:
            with self.conn.cursor() as cur:
                columns = data.keys()
                values = list(data.values())
                query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(values))}) RETURNING id"
                cur.execute(query, values)
                inserted_id = cur.fetchone()[0]
            self.conn.commit()
            return inserted_id
        except psycopg2.Error:
            self.conn.rollback()
            raise

    def find_by_id(self, table: str, document_id: str):
        """Retrieve a single record from a table by its unique ID.

        Args:
            table (str): The name of the database table.
            document_id (str): The unique identifier of the record.

        Returns:
            dict | None: The record as a dictionary if found, otherwise None.
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"SELECT * FROM {table} WHERE id = %s"
                cur.execute(query, (document_id,))
                result = cur.fetchone()
                return dict(result) if result else None
        except psycopg2.Error:
            self.conn.rollback()
            raise

    def find_all(self, table: str):
        """Retrieve all records from a specified table.

        Args:
            table (str): The name of the database table.

        Returns:
            list[dict]: A list of dictionaries representing all records.
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"SELECT * FROM {table}"
                cur.execute(query)
                results = cur.fetchall()
                return [dict(row) for row in results]
        except psycopg2.Error:
            self.conn.rollback()
            raise

    def update(self, table: str, document_id: str, data: dict) -> bool:
        """Update fields of an existing record in a table.

        Args:
            table (str): The name of the database table.
            document_id (str): The unique identifier of the record.
            data (dict): A dictionary containing fields and values to update.

        Returns:
            bool: True if the record was successfully updated, False otherwise.
        """
        try:
            with self.conn.cursor() as cur:
                set_clause = ", ".join([f"{k}=%s" for k in data.keys()])
                values = list(data.values())
                query = f"UPDATE {table} SET {set_clause} WHERE id = %s"
                cur.execute(query, values + [document_id])
                updated = cur.rowcount > 0
            self.conn.commit()
            return updated
        except psycopg2.Error:
            self.conn.rollback()
            raise

    def delete(self, table: str, document_id: str) -> bool:
        """Delete a record from a table using its unique ID.

        Args:
            table (str): The name of the database table.
            document_id (str): The unique identifier of the record.

        Returns:
            bool: True if the record was successfully deleted, False otherwise.
        """
        try:
            with self.conn.cursor() as cur:
                query = f"DELETE FROM {table} WHERE id = %s"
                cur.execute(query, (document_id,))
                deleted = cur.rowcount > 0
            self.conn.commit()
            return deleted
        except psycopg2.Error:
            self.conn.rollback()
            raise

        