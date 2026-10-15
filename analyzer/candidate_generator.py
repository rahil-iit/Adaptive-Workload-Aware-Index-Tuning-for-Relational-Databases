from pathlib import Path
import re


# --------------------------------------------------
# 1. Project and workload location
# --------------------------------------------------

project_folder = Path(__file__).resolve().parent.parent
workload_file = project_folder / "workload" / "workload.sql"


# --------------------------------------------------
# 2. Read workload
# --------------------------------------------------

with open(workload_file, "r") as file:
    workload = file.read()


queries = [
    query.strip()
    for query in workload.split(";")
    if query.strip()
]


# --------------------------------------------------
# 3. Database schema information
# --------------------------------------------------

table_columns = {
    "customer": {
        "customer_id",
        "name",
        "email",
        "city"
    },

    "supplier": {
        "supplier_id",
        "supplier_name",
        "city"
    },

    "product": {
        "product_id",
        "product_name",
        "category",
        "price",
        "supplier_id"
    },

    "orders": {
        "order_id",
        "customer_id",
        "order_date",
        "status",
        "total_amount"
    },

    "orderitem": {
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "price"
    }
}


# --------------------------------------------------
# 4. Table aliases used in workload
# --------------------------------------------------

table_aliases = {
    "o": "orders",
    "c": "customer",
    "oi": "orderitem",
    "p": "product"
}


# --------------------------------------------------
# 5. Candidate storage
# --------------------------------------------------

single_column_candidates = set()
composite_candidates = set()

# Count how many queries use each candidate
candidate_frequency = {}
composite_frequency = {}


# --------------------------------------------------
# 6. Find table used by simple queries
# --------------------------------------------------

def find_main_table(query):

    match = re.search(
        r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        query,
        re.IGNORECASE
    )

    if match:

        table = match.group(1).lower()

        if table in table_columns:
            return table

    return None


# --------------------------------------------------
# 7. Analyze every query
# --------------------------------------------------

for query in queries:

    clean_query = " ".join(query.split())

    main_table = find_main_table(clean_query)

    query_columns = {}


    # ----------------------------------------------
    # A. Find columns in WHERE conditions
    # ----------------------------------------------

    where_match = re.search(
        r"\bWHERE\b(.*?)(?:\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        clean_query,
        re.IGNORECASE
    )

    if where_match:

        where_part = where_match.group(1)


        # Find qualified columns such as:
        # o.customer_id
        # oi.order_id
        # p.category

        qualified_columns = re.findall(
            r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b",
            where_part
        )


        for alias, column in qualified_columns:

            alias = alias.lower()
            column = column.lower()

            table = table_aliases.get(alias)

            if table and column in table_columns[table]:

                if table not in query_columns:
                    query_columns[table] = []

                if column not in query_columns[table]:
                    query_columns[table].append(column)


        # Find unqualified columns such as:
        # customer_id
        # status
        # price
        # order_date

        if main_table:

            for column in table_columns[main_table]:

                pattern = (
                    r"\b"
                    + re.escape(column)
                    + r"\b\s*"
                    r"(?:=|>|<|>=|<=|LIKE|IN|BETWEEN)"
                )

                if re.search(
                    pattern,
                    where_part,
                    re.IGNORECASE
                ):

                    if main_table not in query_columns:
                        query_columns[main_table] = []

                    if column not in query_columns[main_table]:
                        query_columns[main_table].append(column)


    # ----------------------------------------------
    # B. Add single-column candidates
    # ----------------------------------------------

    for table, columns in query_columns.items():

        for column in columns:

            key = (table, column)

            single_column_candidates.add(key)

            # Count this query once
            candidate_frequency[key] = (
                candidate_frequency.get(key, 0) + 1
            )


    # ----------------------------------------------
    # C. Generate composite candidates
    # ----------------------------------------------

    for table, columns in query_columns.items():

        if len(columns) >= 2:

            key = (table, tuple(columns))

            composite_candidates.add(key)

            composite_frequency[key] = (
                composite_frequency.get(key, 0) + 1
            )


    # ----------------------------------------------
    # D. Find GROUP BY columns
    # ----------------------------------------------

    group_match = re.search(
        r"\bGROUP\s+BY\s+(.*?)(?:\bORDER\s+BY\b|\bLIMIT\b|$)",
        clean_query,
        re.IGNORECASE
    )

    if group_match:

        group_part = group_match.group(1)


        # Qualified columns
        qualified_columns = re.findall(
            r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b",
            group_part
        )


        for alias, column in qualified_columns:

            table = table_aliases.get(alias.lower())
            column = column.lower()

            if table and column in table_columns[table]:

                key = (table, column)

                single_column_candidates.add(key)

                candidate_frequency[key] = (
                    candidate_frequency.get(key, 0) + 1
                )


        # Unqualified columns
        if main_table:

            for column in table_columns[main_table]:

                if re.search(
                    r"\b" + re.escape(column) + r"\b",
                    group_part,
                    re.IGNORECASE
                ):

                    key = (main_table, column)

                    single_column_candidates.add(key)

                    candidate_frequency[key] = (
                        candidate_frequency.get(key, 0) + 1
                    )


    # ----------------------------------------------
    # E. Find ORDER BY columns
    # ----------------------------------------------

    order_match = re.search(
        r"\bORDER\s+BY\s+(.*?)(?:\bLIMIT\b|$)",
        clean_query,
        re.IGNORECASE
    )

    if order_match:

        order_part = order_match.group(1)


        # Qualified columns
        qualified_columns = re.findall(
            r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b",
            order_part
        )


        for alias, column in qualified_columns:

            table = table_aliases.get(alias.lower())
            column = column.lower()

            if table and column in table_columns[table]:

                key = (table, column)

                single_column_candidates.add(key)

                candidate_frequency[key] = (
                    candidate_frequency.get(key, 0) + 1
                )


        # Unqualified columns
        if main_table:

            for column in table_columns[main_table]:

                if re.search(
                    r"\b" + re.escape(column) + r"\b",
                    order_part,
                    re.IGNORECASE
                ):

                    key = (main_table, column)

                    single_column_candidates.add(key)

                    candidate_frequency[key] = (
                        candidate_frequency.get(key, 0) + 1
                    )


# --------------------------------------------------
# 8. Display single-column candidates
# --------------------------------------------------

print("\nSingle-column index candidates")
print("--------------------------------")

for table, column in sorted(single_column_candidates):

    frequency = candidate_frequency.get(
        (table, column),
        0
    )

    print(
        f"CREATE INDEX ON {table}({column});"
        f"  -> used by {frequency} workload query(s)"
    )


# --------------------------------------------------
# 9. Display composite candidates
# --------------------------------------------------

print("\nComposite index candidates")
print("--------------------------------")

for table, columns in sorted(composite_candidates):

    frequency = composite_frequency.get(
        (table, columns),
        0
    )

    column_list = ", ".join(columns)

    print(
        f"CREATE INDEX ON {table}({column_list});"
        f"  -> used by {frequency} workload query(s)"
    )


# --------------------------------------------------
# 10. Display totals
# --------------------------------------------------

print(
    "\nTotal single-column candidates:",
    len(single_column_candidates)
)

print(
    "Total composite candidates:",
    len(composite_candidates)
)