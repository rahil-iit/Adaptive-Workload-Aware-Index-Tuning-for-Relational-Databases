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
# Find tables and aliases
# --------------------------------------------------

def get_table_aliases(query):

    aliases = {}

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

        aliases[table] = table

        if alias:

            alias = alias.lower()

            if alias not in sql_keywords:

                aliases[alias] = table

    return aliases


# --------------------------------------------------
# Find column references inside one SQL condition
# --------------------------------------------------

def find_columns_in_text(
    text,
    table,
    columns,
    aliases
):

    found_columns = set()

    table_names = []

    for name, actual_table in aliases.items():

        if actual_table == table:

            table_names.append(name)

    # --------------------------------------------------
    # Qualified references
    #
    # Example:
    # o.customer_id
    # c.city
    # p.price
    # --------------------------------------------------

    for column in columns:

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
                text,
                re.IGNORECASE
            ):

                found_columns.add(column)

    # --------------------------------------------------
    # Unqualified references
    #
    # Example:
    # WHERE status = 'Pending'
    #
    # We only use this when the candidate table is
    # the only table in the query.
    # --------------------------------------------------

    if len(aliases) == 1:

        for column in columns:

            pattern = (
                r"(?<!\.)\b"
                + re.escape(column)
                + r"\b"
            )

            if re.search(
                pattern,
                text,
                re.IGNORECASE
            ):

                found_columns.add(column)

    return found_columns


# --------------------------------------------------
# Find columns used in relevant SQL operations
# --------------------------------------------------

def candidate_used_by_query(
    query,
    table,
    columns
):

    query_lower = query.lower()

    aliases = get_table_aliases(query)

    # Candidate table must exist in query
    if table not in aliases.values():

        return False

    # --------------------------------------------------
    # Store all relevant SQL sections
    # --------------------------------------------------

    relevant_sections = []

    # --------------------------------------------------
    # WHERE section
    # --------------------------------------------------

    where_match = re.search(
        r"\bwhere\b(.*?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    if where_match:

        relevant_sections.append(
            where_match.group(1)
        )

    # --------------------------------------------------
    # JOIN ... ON section
    # --------------------------------------------------

    join_matches = re.findall(
        r"\bon\b(.*?)(?:\bjoin\b|\bwhere\b|\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    for section in join_matches:

        relevant_sections.append(section)

    # --------------------------------------------------
    # GROUP BY section
    # --------------------------------------------------

    group_match = re.search(
        r"\bgroup\s+by\b(.*?)(?:\border\s+by\b|\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    if group_match:

        relevant_sections.append(
            group_match.group(1)
        )

    # --------------------------------------------------
    # ORDER BY section
    # --------------------------------------------------

    order_match = re.search(
        r"\border\s+by\b(.*?)(?:\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    if order_match:

        relevant_sections.append(
            order_match.group(1)
        )

    # --------------------------------------------------
    # Check candidate columns
    # --------------------------------------------------

    found_columns = set()

    for section in relevant_sections:

        found_columns.update(
            find_columns_in_text(
                section,
                table,
                columns,
                aliases
            )
        )

    # --------------------------------------------------
    # Candidate is relevant only if ALL its columns
    # were found.
    #
    # This is important for composite indexes.
    # --------------------------------------------------

    return all(
        column in found_columns
        for column in columns
    )


# --------------------------------------------------
# Get PostgreSQL estimated cost
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
# Get table sizes
# --------------------------------------------------

def get_table_sizes(cursor):

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

        size = cursor.fetchone()[0]

        table_sizes[table] = float(size)

    return table_sizes


# --------------------------------------------------
# Calculate storage cost
# --------------------------------------------------

def calculate_storage_cost(
    table,
    columns,
    table_sizes
):

    table_size = table_sizes[table]

    if len(columns) == 1:

        factor = 0.20

    else:

        factor = 0.30

    return table_size * factor


# --------------------------------------------------
# Calculate candidate scores
# --------------------------------------------------

def calculate_scores():

    queries = read_workload()

    connection = connect_database()

    cursor = connection.cursor()

    table_sizes = get_table_sizes(cursor)

    results = []

    # --------------------------------------------------
    # Analyze candidates
    # --------------------------------------------------

    for table, columns in candidates:

        used_queries = []

        workload_pressure = 0.0

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

                workload_pressure += cost

        storage_cost = calculate_storage_cost(
            table,
            columns,
            table_sizes
        )

        results.append(
            {
                "table": table,
                "columns": columns,
                "queries": used_queries,
                "pressure": workload_pressure,
                "storage": storage_cost
            }
        )

    # --------------------------------------------------
    # Find maximum values
    # --------------------------------------------------

    max_pressure = max(
        item["pressure"]
        for item in results
    )

    max_storage = max(
        item["storage"]
        for item in results
    )

    # --------------------------------------------------
    # Normalize and calculate score
    # --------------------------------------------------

    for item in results:

        if max_pressure > 0:

            normalized_pressure = (
                item["pressure"]
                / max_pressure
            )

        else:

            normalized_pressure = 0.0

        if max_storage > 0:

            normalized_storage = (
                item["storage"]
                / max_storage
            )

        else:

            normalized_storage = 0.0

        item["score"] = (
            0.8 * normalized_pressure
            - 0.2 * normalized_storage
        )

    # --------------------------------------------------
    # Sort by score
    # --------------------------------------------------

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    print("\nCandidate Index Scores")
    print("======================")

    for item in results:

        column_text = ", ".join(
            item["columns"]
        )

        print(
            f"\n{item['table']}({column_text})"
        )

        print(
            f"    Queries : {item['queries']}"
        )

        print(
            f"    Pressure: "
            f"{item['pressure']:.2f}"
        )

        print(
            f"    Storage : "
            f"{item['storage']:.2f} MB"
        )

        print(
            f"    Score   : "
            f"{item['score']:.4f}"
        )

    cursor.close()

    connection.close()


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    calculate_scores()