
# Adaptive Workload-Aware Index Tuning for Relational Databases

A PostgreSQL-based index tuning system that analyzes SQL workloads, generates candidate indexes, estimates query costs and storage overhead, and selects an index configuration using a greedy cost-aware algorithm under a fixed storage budget.

## Overview

Database indexes improve query performance by reducing the amount of data that must be scanned. However, creating too many indexes increases storage consumption and the maintenance overhead of `INSERT`, `UPDATE`, and `DELETE` operations.

This project implements a workload-aware index selection pipeline that identifies promising single-column and composite indexes and selects a configuration based on workload pressure, estimated storage requirements, and maintenance cost.

The system is implemented using **PostgreSQL, Python, SQL, and psycopg2** and is inspired by research on online physical design tuning and cost-driven index selection.

## Objectives

- Analyze a representative SQL workload.
- Measure query execution time and obtain PostgreSQL optimizer cost estimates.
- Generate single-column and composite index candidates.
- Map candidate indexes to potentially relevant workload queries.
- Estimate candidate storage requirements and maintenance overhead.
- Rank candidates using a cost-aware scoring model.
- Select indexes using a greedy strategy under a configurable storage budget.
- Evaluate the selected configuration using physical database experiments.
- Provide a foundation for future adaptive index re-evaluation when workloads change.

## System Architecture

```text
              PostgreSQL Database
                       |
                       v
                SQL Workload
                       |
                       v
               Workload Analysis
                       |
                       v
          Candidate Index Generation
                       |
                       v
             Query-Column Mapping
                       |
                       v
             PostgreSQL Cost Analysis
                       |
                       v
        Storage and Maintenance Estimation
                       |
                       v
              Candidate Scoring
                       |
                       v
             Greedy Index Selection
                       |
                       v
        Storage-Constrained Configuration
                       |
                       v
             Physical Validation
                       |
                       v
        Adaptive Re-evaluation (Extension)
```

## Technology Stack

| Component | Technology |
|---|---|
| Database | PostgreSQL 18 |
| Programming language | Python |
| Database connectivity | psycopg2 |
| Workload definition | SQL |
| Query cost analysis | PostgreSQL `EXPLAIN` |
| Performance validation | `EXPLAIN ANALYZE` |
| Index selection | Greedy heuristic |
| Development environment | Windows / command line |

## Database Design

The experimental database contains five relational tables.

| Table | Rows |
|---|---:|
| Customer | 20,000 |
| Supplier | 1,000 |
| Product | 10,000 |
| Orders | 200,000 |
| OrderItem | 600,000 |
| **Total** | **831,000** |

### Relationships

```text
Customer (1) ---- (N) Orders
Orders   (1) ---- (N) OrderItem
Product  (1) ---- (N) OrderItem
Supplier (1) ---- (N) Product
```

The dataset is generated using SQL scripts and PostgreSQL functions such as `generate_series()` and `random()`.

## Workload

The experimental workload contains 15 representative SQL queries covering:

- Selection and filtering
- JOIN operations
- GROUP BY aggregation
- ORDER BY sorting
- Multiple filtering predicates
- Queries suitable for single-column and composite indexes

Example:

```sql
SELECT *
FROM Orders
WHERE customer_id = 5000;
```

A multiple-predicate example:

```sql
SELECT *
FROM Orders
WHERE status = 'Pending'
  AND order_date > '2026-01-01';
```

## Methodology

### 1. Workload Analysis

The workload analyzer executes the SQL queries and records their execution times. PostgreSQL `EXPLAIN` is also used to obtain estimated query costs, estimated row counts, and execution plans.

Optimizer cost is a relative planning metric; it is not equivalent to execution time in milliseconds.

### 2. Candidate Index Generation

The candidate generator examines relevant columns in `WHERE`, `JOIN`, `GROUP BY`, and `ORDER BY` operations.

Both single-column and composite candidates are considered.

Representative candidates include:

```text
customer(city)
orderitem(order_id)
orders(customer_id)
orders(order_date)
orders(status)
orders(total_amount)
product(category)
product(price)
orders(order_date, customer_id)
orders(order_date, status)
product(price, category)
```

The current prototype generates 11 candidate indexes.

### 3. Query-Column Mapping

Each candidate is associated with workload queries that may benefit from it.

For example:

```text
orders(status)       -> Q2, Q9, Q14
orders(order_date)   -> Q3, Q13, Q14
orders(customer_id)  -> Q1, Q6, Q13
orderitem(order_id)  -> Q7, Q8
```

This mapping is used to estimate the workload pressure associated with each candidate.

### 4. Workload Pressure

The prototype calculates workload pressure as:

\[
Pressure(I) = \sum_{q \in Q(I)} Cost(q)
\]

where:

- \(I\) is a candidate index.
- \(Q(I)\) is the set of workload queries associated with that candidate.
- \(Cost(q)\) is the optimizer-estimated cost of query \(q\).

This is a heuristic measure of workload pressure, not a direct measurement of the cost reduction caused by a hypothetical index.

### 5. Storage Estimation

The current prototype estimates index storage using simplified table-size factors.

For single-column indexes:

\[
Storage(I) \approx 0.20 \times TableSize
\]

For two-column composite indexes:

\[
Storage(I) \approx 0.30 \times TableSize
\]

These factors are implementation assumptions and are not exact PostgreSQL index-size calculations. Actual index size should be measured after physical index creation.

### 6. Maintenance Cost

Indexes introduce additional work when indexed data changes. The prototype models maintenance overhead as:

\[
MaintenanceCost(I)
\approx
WriteFrequency \times Storage(I) \times MaintenanceWeight
\]

The current workload is read-only, so its estimated write-maintenance cost is zero. This does not imply that the selected indexes have zero maintenance overhead for write operations.

### 7. Candidate Scoring

Workload pressure and storage are normalized:

\[
P_{norm} = \frac{Pressure}{MaximumPressure}
\]

\[
S_{norm} = \frac{Storage}{MaximumStorage}
\]

The current scoring model is:

\[
Score(I) = 0.8P_{norm} - 0.2S_{norm}
\]

The weights are configurable prototype choices. They are not prescribed by the reference papers.

### 8. Greedy Index Selection

With \(M\) candidate indexes, there are \(2^M\) possible index configurations. Exhaustive configuration search becomes expensive as the candidate space grows.

The greedy selector incrementally chooses promising candidates while respecting the storage budget.

The prototype uses the following heuristic quantities:

\[
MarginalBenefit(I)
=
\sum_{q \in NewQueries(I)} Cost(q)
\]

\[
Penalty(I)
=
0.05 \times Storage(I)
+
0.05 \times MaintenanceCost(I)
\]

\[
NetGain(I)
=
MarginalBenefit(I) - Penalty(I)
\]

\[
SelectionRatio(I)
=
\frac{NetGain(I)}{Storage(I)}
\]

Here, `NewQueries(I)` refers to queries not already counted as covered by previously selected candidates.

The selector chooses feasible candidates based on their benefit-to-storage ratio and stops when no further candidate can be selected within the storage budget.

**Important implementation detail:** The current selection method is a heuristic. PostgreSQL hypothetical-index cost evaluation is not available in the current environment, so the model does not claim to measure the exact optimizer cost reduction for every candidate configuration.

## Current Prototype Results

The current greedy selection run uses a storage budget of 15 MB.

| Metric | Result |
|---|---:|
| Candidate indexes | 11 |
| Selected indexes | 7 |
| Estimated storage budget | 15 MB |
| Estimated selected storage | 13.45 MB |
| Queries associated with selected candidates | 13 / 15 |
| Write operations in the current workload | 0 |

### Selected Index Configuration

```text
customer(city)
product(price)
orders(status)
orders(customer_id)
orders(total_amount)
product(category)
orders(order_date)
```

Two workload queries, Q7 and Q8, are associated with `orderitem(order_id)`. Its estimated storage is 8.55 MB, while only approximately 1.55 MB remains under the current budget. Therefore, it is not included in the selected configuration.

The 13/15 figure represents heuristic workload coverage based on candidate-to-query mapping. It does not, by itself, prove that all associated queries will execute faster.

## Preliminary Physical Experiment

An initial experiment was conducted for:

```sql
SELECT *
FROM Orders
WHERE customer_id = 5000;
```

| Configuration | Execution time | Observed plan |
|---|---:|---|
| Without index | Approximately 7.924 ms | Sequential Scan |
| With `Orders(customer_id)` index | Approximately 0.112 ms | Bitmap Index Scan and Bitmap Heap Scan |

The improvement for this particular run is:

\[
Improvement(\%) =
\frac{T_{before}-T_{after}}{T_{before}} \times 100
\]

The observed improvement was approximately **98.6%**.

This is a preliminary single-query result, not the final system-wide performance result. Execution times can vary between runs, and a complete before-and-after evaluation of the 15-query workload is still required.

## Project Structure

```text
AdaptiveIndexTuning/
|
|-- analyzer/
|   |-- workload_analyzer.py
|   |-- candidate_generator.py
|   |-- cost_model.py
|   |-- table_statistics.py
|   |-- benefit_calculator.py
|   |-- storage_cost.py
|   |-- maintenance_cost.py
|   |-- candidate_scoring.py
|   |-- index_selector.py
|   `-- greedy_selector.py
|
|-- config/
|   `-- config.py
|
|-- database/
|   |-- schema.sql
|   |-- sample_data.sql
|   `-- orderitem_data.sql
|
|-- workload/
|   `-- workload.sql
|
|-- experiments/
|   `-- results/
|
`-- README.md
```

### Module Responsibilities

| File | Responsibility |
|---|---|
| `workload_analyzer.py` | Measures workload query execution times |
| `candidate_generator.py` | Generates candidate indexes |
| `cost_model.py` | Retrieves PostgreSQL optimizer costs |
| `table_statistics.py` | Collects table row counts and sizes |
| `benefit_calculator.py` | Maps candidates to workload queries |
| `storage_cost.py` | Estimates index storage |
| `maintenance_cost.py` | Estimates write-maintenance overhead |
| `candidate_scoring.py` | Scores index candidates |
| `index_selector.py` | Represents index configurations |
| `greedy_selector.py` | Selects indexes under a storage budget |

## Installation and Setup

### Prerequisites

- PostgreSQL 18 or a compatible PostgreSQL version
- Python 3
- pip

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AdaptiveIndexTuning
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the actual repository URL.

### 2. Install the Python dependency

```bash
python -m pip install psycopg2-binary
```

### 3. Create the database

Open `psql` and run:

```sql
CREATE DATABASE index_tuning;
```

Connect to it:

```sql
\c index_tuning
```

### 4. Configure the database connection

Update `config/config.py` with your local PostgreSQL credentials.

Do not commit passwords or other secrets to Git. Use environment variables or a local configuration file excluded from version control for sensitive settings.

### 5. Create the schema and load data

From `psql`, execute the scripts using their actual local paths:

```sql
\i 'path/to/database/schema.sql'
\i 'path/to/database/sample_data.sql'
\i 'path/to/database/orderitem_data.sql'
```

Run the data-loading scripts only once for a fresh database unless the tables have been cleared or the scripts are designed to avoid duplicate insertion.

### 6. Run the workload analyzer

From the repository root:

```bash
python -m analyzer.workload_analyzer
```

Other modules can be run similarly:

```bash
python -m analyzer.cost_model
python -m analyzer.table_statistics
python -m analyzer.benefit_calculator
python -m analyzer.storage_cost
python -m analyzer.maintenance_cost
python -m analyzer.candidate_scoring
python -m analyzer.greedy_selector
```

These commands assume the corresponding modules are executable and that the database connection is configured correctly.

## Research Foundation

The project is inspired by the following papers:

1. Nicolas Bruno and Surajit Chaudhuri, *An Online Approach to Physical Design Tuning*.
2. Sanjay Agrawal, Eric Chu and Vivek Narasayya, *Automatic Physical Design Tuning: Workload as a Sequence*.
3. Surajit Chaudhuri and Vivek Narasayya, *An Efficient, Cost-Driven Index Selection Tool for Microsoft SQL Server*.

The implementation follows their broad methodology for workload-aware physical design, candidate index selection, and cost-aware configuration search. It does not claim to reproduce their exact algorithms or system-specific optimizer interfaces.

## Limitations and Future Work

The current prototype has the following limitations:

- Candidate benefit is estimated using heuristic workload pressure rather than true hypothetical-index optimizer evaluation.
- Storage estimates use simplified table-size factors.
- Maintenance cost is approximate, and the current workload contains no write operations.
- Query occurrence in the constructed workload is not equivalent to real production query frequency.
- Complete physical validation across all 15 queries remains necessary.
- Adaptive workload-change detection and automatic index creation/deletion are future extensions.

Planned work includes:

1. Establishing a baseline for all 15 queries.
2. Physically creating the selected indexes.
3. Measuring query execution times before and after selection.
4. Calculating total workload performance improvement.
5. Evaluating actual index sizes and write overhead.
6. Introducing a changed workload and re-evaluating candidate benefits.
7. Developing adaptive index creation/deletion decisions.
8. Using thresholds or hysteresis to reduce unnecessary index create/drop oscillation.

## Conclusion

This project implements a PostgreSQL-based prototype for workload-aware index candidate generation and storage-constrained greedy selection. It integrates workload analysis, query-cost information, query-to-index mapping, storage estimation, maintenance-cost modeling, and candidate scoring into a single pipeline.

The current prototype selects seven indexes under an estimated 15 MB storage budget, with 13 of the 15 workload queries associated with the selected candidates. Preliminary single-query testing also demonstrates that a suitable index can substantially reduce execution time.

Full workload-level performance validation and adaptive re-evaluation are the next steps toward a more complete workload-aware index tuning system.
