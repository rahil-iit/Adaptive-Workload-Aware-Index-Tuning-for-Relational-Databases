# --------------------------------------------------
# Candidate Index
# --------------------------------------------------

class IndexCandidate:

    def __init__(
        self,
        table,
        columns,
        frequency
    ):

        self.table = table
        self.columns = tuple(columns)
        self.frequency = frequency

        self.workload_benefit = 0
        self.score = 0

    def calculate_benefit(self, query_costs):

        self.workload_benefit = 0

        for query_number in self.frequency:

            if query_number in query_costs:

                self.workload_benefit += query_costs[query_number]

        return self.workload_benefit


# --------------------------------------------------
# Index Configuration
# --------------------------------------------------

class IndexConfiguration:

    def __init__(self):

        self.indexes = set()

    def add_index(self, table, columns):

        index = (
            table,
            tuple(columns)
        )

        self.indexes.add(index)

    def remove_index(self, table, columns):

        index = (
            table,
            tuple(columns)
        )

        if index in self.indexes:

            self.indexes.remove(index)

    def show_indexes(self):

        if not self.indexes:

            print("No indexes selected.")

            return

        print("\nSelected Indexes")
        print("----------------")

        for table, columns in sorted(self.indexes):

            column_list = ", ".join(columns)

            print(
                f"{table}({column_list})"
            )


# --------------------------------------------------
# Test
# --------------------------------------------------

if __name__ == "__main__":

    # Example query costs
    query_costs = {
        1: 3971.0,
        2: 2000.0,
        3: 1500.0,
        4: 1000.0
    }

    # Example candidate used by
    # queries 1 and 3
    candidate = IndexCandidate(
        table="orders",
        columns=["customer_id"],
        frequency=[1, 3]
    )

    benefit = candidate.calculate_benefit(
        query_costs
    )

    print("Candidate Index")
    print("----------------")

    print(
        f"Table   : {candidate.table}"
    )

    print(
        f"Columns : {candidate.columns}"
    )

    print(
        f"Queries : {candidate.frequency}"
    )

    print(
        f"Benefit : {benefit:.2f}"
    )