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
# Configuration parameters
# --------------------------------------------------

STORAGE_BUDGET_MB = 15.0

STORAGE_WEIGHT = 0.05

MAINTENANCE_WEIGHT = 0.05


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

    # Remove SQL comments
    content = re.sub(
        r"--.*",
        "",
        content
    )

    queries = []

    for query in content.split(";"):

        query = query.strip()

        if query:

            queries.append(query)

    return queries


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
# Find relevant SQL sections
# --------------------------------------------------

def get_relevant_sections(query):

    query_lower = query.lower()

    sections = []

    # WHERE
    where_match = re.search(
        r"\bwhere\b(.*?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    if where_match:

        sections.append(
            where_match.group(1)
        )

    # JOIN ON
    join_matches = re.findall(
        r"\bon\b(.*?)(?:\bjoin\b|\bwhere\b|\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    sections.extend(
        join_matches
    )

    # GROUP BY
    group_match = re.search(
        r"\bgroup\s+by\b(.*?)(?:\border\s+by\b|\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    if group_match:

        sections.append(
            group_match.group(1)
        )

    # ORDER BY
    order_match = re.search(
        r"\border\s+by\b(.*?)(?:\blimit\b|$)",
        query_lower,
        re.IGNORECASE | re.DOTALL
    )

    if order_match:

        sections.append(
            order_match.group(1)
        )

    return sections


# --------------------------------------------------
# Check candidate usage
# --------------------------------------------------

def candidate_used_by_query(
    query,
    table,
    columns
):

    aliases = get_table_aliases(
        query
    )

    if table not in aliases.values():

        return False

    table_names = []

    for name, actual_table in aliases.items():

        if actual_table == table:

            table_names.append(
                name
            )

    sections = get_relevant_sections(
        query
    )

    found_columns = set()

    for section in sections:

        # Qualified references
        for name in table_names:

            for column in columns:

                pattern = (
                    r"\b"
                    + re.escape(name)
                    + r"\s*\.\s*"
                    + re.escape(column)
                    + r"\b"
                )

                if re.search(
                    pattern,
                    section,
                    re.IGNORECASE
                ):

                    found_columns.add(
                        column
                    )

        # Unqualified references
        if len(aliases) == 1:

            for column in columns:

                pattern = (
                    r"(?<!\.)\b"
                    + re.escape(column)
                    + r"\b"
                )

                if re.search(
                    pattern,
                    section,
                    re.IGNORECASE
                ):

                    found_columns.add(
                        column
                    )

    return all(
        column in found_columns
        for column in columns
    )


# --------------------------------------------------
# Get PostgreSQL estimated query cost
# --------------------------------------------------

def get_query_cost(
    cursor,
    query
):

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

        return float(
            match.group(1)
        )

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

    sizes = {}

    for table in tables:

        cursor.execute(
            f"""
            SELECT
                pg_total_relation_size('{table}')
                / 1024.0 / 1024.0;
            """
        )

        sizes[table] = float(
            cursor.fetchone()[0]
        )

    return sizes


# --------------------------------------------------
# Estimate index storage
# --------------------------------------------------

def estimate_storage(
    table,
    columns,
    table_sizes
):

    table_size = table_sizes[
        table
    ]

    if len(columns) == 1:

        factor = 0.20

    else:

        factor = 0.30

    return table_size * factor


# --------------------------------------------------
# Identify write operations
# --------------------------------------------------

def get_write_table(query):

    query = query.strip()

    insert_match = re.search(
        r"\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        query,
        re.IGNORECASE
    )

    if insert_match:

        return insert_match.group(1).lower()

    update_match = re.search(
        r"\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        query,
        re.IGNORECASE
    )

    if update_match:

        return update_match.group(1).lower()

    delete_match = re.search(
        r"\bDELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        query,
        re.IGNORECASE
    )

    if delete_match:

        return delete_match.group(1).lower()

    return None


# --------------------------------------------------
# Calculate write frequency
# --------------------------------------------------

def calculate_write_frequency(
    queries
):

    write_frequency = {}

    for query in queries:

        table = get_write_table(
            query
        )

        if table is None:

            continue

        if table not in write_frequency:

            write_frequency[table] = 0

        write_frequency[table] += 1

    return write_frequency


# --------------------------------------------------
# Maintenance cost
# --------------------------------------------------

def calculate_maintenance_cost(
    table,
    storage,
    write_frequency
):

    writes = write_frequency.get(
        table,
        0
    )

    return (
        writes
        * storage
        * MAINTENANCE_WEIGHT
    )


# --------------------------------------------------
# Build candidate information
# --------------------------------------------------

def build_candidates(
    cursor,
    queries,
    table_sizes,
    write_frequency
):

    candidate_information = []

    for table, columns in candidates:

        query_numbers = []

        total_pressure = 0.0

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

                query_numbers.append(
                    query_number
                )

                total_pressure += cost

        storage = estimate_storage(
            table,
            columns,
            table_sizes
        )

        maintenance = (
            calculate_maintenance_cost(
                table,
                storage,
                write_frequency
            )
        )

        candidate_information.append(
            {
                "table": table,
                "columns": columns,
                "queries": query_numbers,
                "pressure": total_pressure,
                "storage": storage,
                "maintenance": maintenance
            }
        )

    return candidate_information


# --------------------------------------------------
# Calculate marginal gain
# --------------------------------------------------

def calculate_marginal_gain(
    candidate,
    covered_queries,
    query_costs
):

    marginal_benefit = 0.0

    new_queries = []

    for query_number in candidate[
        "queries"
    ]:

        if query_number not in covered_queries:

            marginal_benefit += (
                query_costs[
                    query_number
                ]
            )

            new_queries.append(
                query_number
            )

    # --------------------------------------------------
    # Penalize storage and maintenance
    # --------------------------------------------------

    penalty = (
        STORAGE_WEIGHT
        * candidate["storage"]
        +
        MAINTENANCE_WEIGHT
        * candidate["maintenance"]
    )

    net_gain = (
        marginal_benefit
        - penalty
    )

    return (
        net_gain,
        marginal_benefit,
        new_queries
    )


# --------------------------------------------------
# Greedy selection
# --------------------------------------------------

def select_configuration(
    candidate_information,
    query_costs
):

    selected = []

    covered_queries = set()

    used_storage = 0.0

    remaining = (
        candidate_information.copy()
    )

    print(
        "\nGreedy Configuration Selection"
    )

    print(
        "=============================="
    )

    while remaining:

        best_candidate = None

        best_gain = 0.0

        best_benefit = 0.0

        best_new_queries = []

        # --------------------------------------------------
        # Evaluate every remaining candidate
        # --------------------------------------------------

        for candidate in remaining:

            (
                gain,
                benefit,
                new_queries
            ) = calculate_marginal_gain(
                candidate,
                covered_queries,
                query_costs
            )

            if benefit <= 0:

                continue

            if (
                used_storage
                + candidate["storage"]
                > STORAGE_BUDGET_MB
            ):

                continue

            # --------------------------------------------------
            # Gain per MB
            # --------------------------------------------------

            gain_per_mb = (
                gain
                / candidate["storage"]
            )

            if (
                best_candidate is None
                or gain_per_mb
                > best_candidate[
                    "gain_per_mb"
                ]
            ):

                best_candidate = (
                    candidate
                )

                best_candidate[
                    "gain_per_mb"
                ] = gain_per_mb

                best_gain = gain

                best_benefit = benefit

                best_new_queries = (
                    new_queries
                )

        # --------------------------------------------------
        # Stop if no candidate is useful
        # --------------------------------------------------

        if best_candidate is None:

            break

        # --------------------------------------------------
        # Add selected candidate
        # --------------------------------------------------

        selected.append(
            best_candidate
        )

        used_storage += (
            best_candidate[
                "storage"
            ]
        )

        covered_queries.update(
            best_new_queries
        )

        remaining.remove(
            best_candidate
        )

        columns = ", ".join(
            best_candidate[
                "columns"
            ]
        )

        print(
            f"\nSelected: "
            f"{best_candidate['table']}"
            f"({columns})"
        )

        print(
            f"    Marginal Benefit : "
            f"{best_benefit:.2f}"
        )

        print(
            f"    Maintenance Cost : "
            f"{best_candidate['maintenance']:.2f}"
        )

        print(
            f"    Net Gain         : "
            f"{best_gain:.2f}"
        )

        print(
            f"    New Queries      : "
            f"{best_new_queries}"
        )

        print(
            f"    Storage          : "
            f"{best_candidate['storage']:.2f} MB"
        )

        print(
            f"    Total Storage    : "
            f"{used_storage:.2f} MB"
        )

    return (
        selected,
        used_storage,
        covered_queries
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    queries = read_workload()

    connection = connect_database()

    cursor = connection.cursor()

    # --------------------------------------------------
    # Table statistics
    # --------------------------------------------------

    table_sizes = get_table_sizes(
        cursor
    )

    # --------------------------------------------------
    # Query costs
    # --------------------------------------------------

    query_costs = {}

    for query_number, query in enumerate(
        queries,
        start=1
    ):

        query_costs[
            query_number
        ] = get_query_cost(
            cursor,
            query
        )

    # --------------------------------------------------
    # Write frequency
    # --------------------------------------------------

    write_frequency = (
        calculate_write_frequency(
            queries
        )
    )

    # --------------------------------------------------
    # Candidate information
    # --------------------------------------------------

    candidate_information = (
        build_candidates(
            cursor,
            queries,
            table_sizes,
            write_frequency
        )
    )

    # --------------------------------------------------
    # Greedy selection
    # --------------------------------------------------

    (
        selected,
        used_storage,
        covered_queries
    ) = select_configuration(
        candidate_information,
        query_costs
    )

    # --------------------------------------------------
    # Final configuration
    # --------------------------------------------------

    print(
        "\n\nFinal Index Configuration"
    )

    print(
        "========================="
    )

    for candidate in selected:

        columns = ", ".join(
            candidate["columns"]
        )

        print(
            f"{candidate['table']}"
            f"({columns})"
        )

    print(
        f"\nTotal Storage : "
        f"{used_storage:.2f} MB"
    )

    print(
        f"Storage Budget: "
        f"{STORAGE_BUDGET_MB:.2f} MB"
    )

    print(
        f"Covered Queries: "
        f"{len(covered_queries)} / "
        f"{len(queries)}"
    )

    cursor.close()

    connection.close()


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":

    main()