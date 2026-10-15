import psycopg2

from config.config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
)


# --------------------------------------------------
# Database connection
# --------------------------------------------------

def connect_database():

    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


# --------------------------------------------------
# Table sizes in MB
# --------------------------------------------------

def get_table_sizes():

    connection = connect_database()

    cursor = connection.cursor()

    tables = [
        "customer",
        "supplier",
        "product",
        "orders",
        "orderitem"
    ]

    table_sizes = {}

    for table in tables:

        cursor.execute(
            f"""
            SELECT
                pg_total_relation_size('{table}')
                / 1024.0 / 1024.0;
            """
        )

        size_mb = cursor.fetchone()[0]

        table_sizes[table] = size_mb

    cursor.close()

    connection.close()

    return table_sizes


# --------------------------------------------------
# Estimate index storage cost
# --------------------------------------------------

def estimate_storage_cost(
    table,
    columns,
    table_sizes
):

    table_size = float(table_sizes[table])

    number_of_columns = len(columns)

    if number_of_columns == 1:

        index_factor = 0.20

    else:

        index_factor = 0.30

    estimated_size = (
        table_size * index_factor
    )

    return estimated_size


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    table_sizes = get_table_sizes()

    candidates = [

        ("customer", ("city",)),

        ("orderitem", ("order_id",)),

        ("orders", ("customer_id",)),

        ("orders", ("order_date",)),

        ("orders", ("status",)),

        ("orders", ("total_amount",)),

        ("product", ("category",)),

        ("product", ("price",)),

        ("orders", ("order_date", "customer_id")),

        ("orders", ("order_date", "status")),

        ("product", ("price", "category"))
    ]

    print("\nEstimated Index Storage")
    print("=======================")

    for table, columns in candidates:

        storage = estimate_storage_cost(
            table,
            columns,
            table_sizes
        )

        column_text = ", ".join(columns)

        print(
            f"{table}({column_text})"
        )

        print(
            f"    Table Size : "
            f"{table_sizes[table]:.2f} MB"
        )

        print(
            f"    Est. Index : "
            f"{storage:.2f} MB"
        )