import re
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
# Read workload
# --------------------------------------------------

def read_workload():

    with open(
        "workload/workload.sql",
        "r",
        encoding="utf-8"
    ) as file:

        content = file.read()

    queries = []

    for query in content.split(";"):

        query = query.strip()

        if query:

            queries.append(query)

    return queries


# --------------------------------------------------
# Candidate indexes
# --------------------------------------------------

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


# --------------------------------------------------
# Find tables and aliases used in a query
# --------------------------------------------------

def get_table_aliases(query):

    aliases = {}

    sql_tables = [
        "customer",
        "supplier",
        "product",
        "orders",
        "orderitem"
    ]

    sql_keywords = {
        "where",
        "join",
        "on",
        "group",
        "order",
        "having",
        "limit",
        "offset",
        "left",
        "right",
        "inner",
        "outer",
        "full",
        "cross",
        "and",
        "or"
    }

    # --------------------------------------------------
    # Find tables after FROM or JOIN
    #
    # Examples:
    #
    # FROM Orders
    # FROM Orders o
    # FROM Orders AS o
    # JOIN Customer c
    # JOIN Product AS p
    # --------------------------------------------------

    pattern = r"""
        \b
        (?:FROM|JOIN)
        \s+
        (customer|supplier|product|orders|orderitem)
        \b
        (?:
            \s+
            (?:AS\s+)?
            ([a-zA-Z_][a-zA-Z0-9_]*)
        )?
    """

    matches = re.findall(
        pattern,
        query,
        re.IGNORECASE | re.VERBOSE
    )

    for table, alias in matches:

        table = table.lower()

        # Always map the actual table name
        aliases[table] = table

        # Store alias if it is actually an alias
        if alias:

            alias = alias.lower()

            if alias not in sql_keywords:

                aliases[alias] = table

    return aliases


# --------------------------------------------------
# Check whether candidate is used by query
# --------------------------------------------------

def candidate_used_by_query(
    query,
    table,
    columns
):

    query_lower = query.lower()

    aliases = get_table_aliases(query)

    # --------------------------------------------------
    # Candidate table must actually occur in query
    # --------------------------------------------------

    if table not in aliases.values():

        return False

    # --------------------------------------------------
    # Get names referring to this table
    #
    # Example:
    #
    # Orders o
    #
    # gives:
    #
    # orders
    # o
    # --------------------------------------------------

    table_names = []

    for name, actual_table in aliases.items():

        if actual_table == table:

            table_names.append(name)

    # --------------------------------------------------
    # Check every candidate column
    # --------------------------------------------------

    for column in columns:

        column_found = False

        # --------------------------------------------------
        # First check qualified references
        #
        # Examples:
        #
        # o.customer_id
        # orders.customer_id
        # c.city
        # p.price
        # --------------------------------------------------

        for name in table_names:

            pattern = (
                r"\b"
                + re.escape(name)
                + r"\s*\.\s*"
                + re.escape(column)
                + r"\b"
            )

            if re.search(
                pattern,
                query_lower
            ):

                column_found = True

                break

        # --------------------------------------------------
        # Check unqualified column
        #
        # Examples:
        #
        # WHERE status = 'Pending'
        # WHERE price > 5000
        #
        # We allow this when the column appears without
        # a table qualifier.
        # --------------------------------------------------

        if not column_found:

            pattern = (
                r"(?<!\.)\b"
                + re.escape(column)
                + r"\b"
            )

            if re.search(
                pattern,
                query_lower
            ):

                column_found = True

        # --------------------------------------------------
        # If even one column of a composite candidate
        # is missing, the candidate is not associated
        # with this query.
        # --------------------------------------------------

        if not column_found:

            return False

    return True


# --------------------------------------------------
# Get PostgreSQL estimated query cost
# --------------------------------------------------

def get_query_cost(cursor, query):

    cursor.execute(
        "EXPLAIN " + query
    )

    plan = cursor.fetchall()

    if not plan:

        return 0.0

    first_line = plan[0][0]

    match = re.search(
        r"cost=[0-9.]+\.\.([0-9.]+)",
        first_line
    )

    if match:

        return float(match.group(1))

    return 0.0


# --------------------------------------------------
# Calculate candidate workload pressure
# --------------------------------------------------

def calculate_candidate_scores():

    queries = read_workload()

    connection = connect_database()

    cursor = connection.cursor()

    print("\nCandidate Workload Analysis")
    print("===========================")

    results = []

    # --------------------------------------------------
    # Check every candidate
    # --------------------------------------------------

    for table, columns in candidates:

        used_queries = []

        total_cost = 0.0

        # --------------------------------------------------
        # Check every workload query
        # --------------------------------------------------

        for query_number, query in enumerate(
            queries,
            start=1
        ):

            if candidate_used_by_query(
                query,
                table,
                columns
            ):

                cost = get_query_cost(
                    cursor,
                    query
                )

                used_queries.append(
                    query_number
                )

                total_cost += cost

        results.append(
            (
                table,
                columns,
                used_queries,
                total_cost
            )
        )

    # --------------------------------------------------
    # Sort candidates by workload pressure
    # --------------------------------------------------

    results.sort(
        key=lambda item: item[3],
        reverse=True
    )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    for table, columns, used_queries, total_cost in results:

        column_text = ", ".join(columns)

        print(
            f"{table}({column_text})"
        )

        print(
            f"    Queries : {used_queries}"
        )

        print(
            f"    Count   : {len(used_queries)}"
        )

        print(
            f"    Pressure: {total_cost:.2f}"
        )

    # --------------------------------------------------
    # Close database
    # --------------------------------------------------

    cursor.close()

    connection.close()


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    calculate_candidate_scores()