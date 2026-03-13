import psycopg2

class PostgresRepository:

    def __init__(self):
        self.conn = psycopg2.connect(
            host="localhost",
            database="bierdb",
            user="postgres",
            password="postgres"
        )

    def insert(self, table, data):
        cur = self.conn.cursor()

        columns = data.keys()
        values = data.values()

        query = f"""
        INSERT INTO {table} ({','.join(columns)})
        VALUES ({','.join(['%s'] * len(values))})
        RETURNING id
        """

        cur.execute(query, list(values))
        self.conn.commit()

        return cur.fetchone()[0]