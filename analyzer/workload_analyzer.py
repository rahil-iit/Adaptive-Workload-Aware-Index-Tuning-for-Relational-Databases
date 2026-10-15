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


# Connect to PostgreSQL
connection = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

print("Connected to PostgreSQL successfully!")


# Find workload.sql
project_folder = Path(__file__).resolve().parent.parent
workload_file = project_folder / "workload" / "workload.sql"


# Read workload
with open(workload_file, "r") as file:
    workload = file.read()


# Split workload into individual queries
queries = [
    query.strip()
    for query in workload.split(";")
    if query.strip()
]


print("Total workload queries:", len(queries))


cursor = connection.cursor()

results = []


# Analyze every query
for number, query in enumerate(queries, start=1):

    explain_query = "EXPLAIN (ANALYZE, BUFFERS) " + query

    cursor.execute(explain_query)

    plan = cursor.fetchall()

    execution_time = None

    # Find Execution Time from PostgreSQL output
    for row in plan:

        line = row[0]

        if line.startswith("Execution Time:"):

            match = re.search(r"Execution Time:\s*([0-9.]+)", line)

            if match:
                execution_time = float(match.group(1))

    results.append({
        "query_number": number,
        "execution_time": execution_time
    })


cursor.close()
connection.close()


print("\nWorkload Analysis Results")
print("-------------------------")

for result in results:

    print(
        f"Query {result['query_number']:2d}"
        f"  ->  {result['execution_time']:.3f} ms"
    )


print("\nConnection closed.")