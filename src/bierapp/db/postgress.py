import os

import psycopg2
from psycopg2.extras import RealDictCursor


class PostgresRepository:
    """Repository handling Postgres database operations."""

    def __init__(self):
        self.conn = None

    def connect(self):
        """
        Establish a connection to the Postgres database if none exists.

        Returns:
            None: No return value.
        """
        if self.conn is None:
            self.conn = psycopg2.connect(
                host=os.environ.get("POSTGRES_HOST", "localhost"),
                port=int(os.environ.get("POSTGRES_PORT", 5432)),
                database=os.environ.get("POSTGRES_DB", "lagerverwaltung"),
                user=os.environ.get("POSTGRES_USER", "admin"),
                password=os.environ.get("POSTGRES_PASSWORD", "secret")
            )

    def insert(self, table: str, data: dict) -> str:
        """
        Insert a new record into the specified table.

        Args:
            table (str): The name of the database table where the record will be inserted.
            data (dict): A dictionary containing column names as keys and the values to insert.

        Returns:
            str: The ID of the newly inserted record.
        """
        with self.conn.cursor() as cur:

            columns = data.keys()
            values = list(data.values())

            query = f"""
            INSERT INTO {table} ({','.join(columns)})
            VALUES ({','.join(['%s'] * len(values))})
            RETURNING id
            """

            cur.execute(query, values)
            self.conn.commit()

            return cur.fetchone()[0]

    def find_by_id(self, table: str, document_id: str):
        """
        Retrieve a single record from a table by its unique ID.

        Args:
            table (str): The name of the database table to query.
            document_id (str): The unique identifier of the record.

        Returns:
            dict | None: The record as a dictionary if found, otherwise None.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:

            query = f"SELECT * FROM {table} WHERE id = %s"

            cur.execute(query, (document_id,))
            result = cur.fetchone()

            return dict(result) if result else None


    def find_all(self, table: str):
        """
        Retrieve all records from a specified table.

        Args:
            table (str): The name of the database table to query.

        Returns:
            list[dict]: A list of dictionaries representing all records in the table.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:

            query = f"SELECT * FROM {table}"

            cur.execute(query)
            results = cur.fetchall()

            return [dict(row) for row in results]

    def update(self, table: str, document_id: str, data: dict) -> bool:
        """
        Update fields of an existing record in a table.

        Args:
            table (str): The name of the database table containing the record.
            document_id (str): The unique identifier of the record to update.
            data (dict): A dictionary containing the fields and values to update.

        Returns:
            bool: True if the record was successfully updated, otherwise False.
        """
        with self.conn.cursor() as cur:

            set_clause = ", ".join([f"{k}=%s" for k in data.keys()])
            values = list(data.values())

            query = f"""
            UPDATE {table}
            SET {set_clause}
            WHERE id = %s
            """

            cur.execute(query, values + [document_id])
            self.conn.commit()

            return cur.rowcount > 0

    def delete(self, table: str, document_id: str) -> bool:
        """
        Delete a record from a table using its unique ID.

        Args:
            table (str): The name of the database table containing the record.
            document_id (str): The unique identifier of the record to delete.

        Returns:
            bool: True if the record was successfully deleted, otherwise False.
    """
        with self.conn.cursor() as cur:

            query = f"DELETE FROM {table} WHERE id = %s"

            cur.execute(query, (document_id,))
            self.conn.commit()

            return cur.rowcount > 0