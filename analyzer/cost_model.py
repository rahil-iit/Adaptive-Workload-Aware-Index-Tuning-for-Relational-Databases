from pathlib import Path
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
# 1. Connect to PostgreSQL
# --------------------------------------------------

connection = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

print("Connected to PostgreSQL successfully!")


# --------------------------------------------------
# 2. Find workload file
# --------------------------------------------------

project_folder = Path(__file__).resolve().parent.parent
workload_file = project_folder / "workload" / "workload.sql"


# --------------------------------------------------
# 3. Read workload
# --------------------------------------------------

with open(workload_file, "r") as file:
    workload = file.read()


queries = [
    query.strip()
    for query in workload.split(";")
    if query.strip()
]


print("Total workload queries:", len(queries))


# --------------------------------------------------
# 4. Cursor
# --------------------------------------------------

cursor = connection.cursor()

results = []


# --------------------------------------------------
# 5. Analyze each query
# --------------------------------------------------

for number, query in enumerate(queries, start=1):

    explain_query = "EXPLAIN " + query

    cursor.execute(explain_query)

    plan = cursor.fetchall()


    estimated_cost = None
    estimated_rows = None


    # ----------------------------------------------
    # First line of PostgreSQL plan
    # Example:
    #
    # Seq Scan on orders
    # (cost=0.00..3971.00 rows=39407 width=27)
    # ----------------------------------------------

    first_line = plan[0][0]


    cost_match = re.search(
        r"cost=([0-9.]+)\.\.([0-9.]+)",
        first_line
    )

    rows_match = re.search(
        r"rows=([0-9]+)",
        first_line
    )


    if cost_match:

        startup_cost = float(
            cost_match.group(1)
        )

        total_cost = float(
            cost_match.group(2)
        )

        estimated_cost = total_cost


    if rows_match:

        estimated_rows = int(
            rows_match.group(1)
        )


    results.append({
        "query_number": number,
        "estimated_cost": estimated_cost,
        "estimated_rows": estimated_rows
    })


# --------------------------------------------------
# 6. Close connection
# --------------------------------------------------

cursor.close()
connection.close()


# --------------------------------------------------
# 7. Display results
# --------------------------------------------------

print("\nPostgreSQL Cost Analysis")
print("------------------------")

for result in results:

    print(
        f"Query {result['query_number']:2d}"
        f" -> Estimated Cost: "
        f"{result['estimated_cost']:.2f}"
        f" | Estimated Rows: "
        f"{result['estimated_rows']}"
    )


print("\nConnection closed.")