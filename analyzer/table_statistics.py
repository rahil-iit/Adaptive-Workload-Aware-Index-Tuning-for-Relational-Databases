import psycopg2

from config.config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
)


def get_table_statistics():

    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    cursor = connection.cursor()

    tables = [
        "customer",
        "supplier",
        "product",
        "orders",
        "orderitem"
    ]

    print("\nTable Statistics")
    print("----------------")

    for table in tables:

        cursor.execute(
            f"""
            SELECT
                COUNT(*),
                pg_size_pretty(
                    pg_total_relation_size('{table}')
                )
            FROM {table};
            """
        )

        row_count, table_size = cursor.fetchone()

        print(
            f"{table:10} -> "
            f"Rows: {row_count:8} | "
            f"Size: {table_size}"
        )

    cursor.close()
    connection.close()


if __name__ == "__main__":

    get_table_statistics()