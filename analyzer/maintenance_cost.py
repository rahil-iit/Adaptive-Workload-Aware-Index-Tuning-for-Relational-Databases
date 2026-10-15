import re


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

    # --------------------------------------------------
    # Remove SQL comments
    # --------------------------------------------------

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
# Identify operation type
# --------------------------------------------------

def get_operation_type(query):

    # Remove leading whitespace
    query = query.strip()

    # Find first SQL keyword
    match = re.match(
        r"^(SELECT|INSERT|UPDATE|DELETE)\b",
        query,
        re.IGNORECASE
    )

    if not match:

        return "OTHER"

    return match.group(1).upper()


# --------------------------------------------------
# Find table affected by write operation
# --------------------------------------------------

def get_write_table(query):

    query = query.strip()

    # INSERT INTO table
    insert_match = re.search(
        r"\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        query,
        re.IGNORECASE
    )

    if insert_match:

        return insert_match.group(1).lower()

    # UPDATE table
    update_match = re.search(
        r"\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        query,
        re.IGNORECASE
    )

    if update_match:

        return update_match.group(1).lower()

    # DELETE FROM table
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

def calculate_write_frequency(queries):

    write_frequency = {}

    for query in queries:

        operation = get_operation_type(query)

        if operation == "SELECT":

            continue

        table = get_write_table(query)

        if table is None:

            continue

        if table not in write_frequency:

            write_frequency[table] = 0

        write_frequency[table] += 1

    return write_frequency


# --------------------------------------------------
# Calculate maintenance cost
# --------------------------------------------------

def calculate_maintenance_cost(
    table,
    index_storage,
    write_frequency
):

    writes = write_frequency.get(
        table,
        0
    )

    maintenance_weight = 1.0

    return (
        writes
        * index_storage
        * maintenance_weight
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    queries = read_workload()

    write_frequency = calculate_write_frequency(
        queries
    )

    print("\nWorkload Operation Analysis")
    print("===========================")

    select_count = 0
    insert_count = 0
    update_count = 0
    delete_count = 0

    for query in queries:

        operation = get_operation_type(query)

        if operation == "SELECT":

            select_count += 1

        elif operation == "INSERT":

            insert_count += 1

        elif operation == "UPDATE":

            update_count += 1

        elif operation == "DELETE":

            delete_count += 1

    print(
        f"SELECT : {select_count}"
    )

    print(
        f"INSERT : {insert_count}"
    )

    print(
        f"UPDATE : {update_count}"
    )

    print(
        f"DELETE : {delete_count}"
    )

    print("\nWrite Frequency by Table")
    print("========================")

    if not write_frequency:

        print(
            "No write operations found."
        )

        print(
            "Maintenance cost for the "
            "current workload is therefore 0."
        )

    else:

        for table, count in sorted(
            write_frequency.items()
        ):

            print(
                f"{table:10} -> "
                f"{count} write operation(s)"
            )