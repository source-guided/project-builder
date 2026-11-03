# Reconcile two CSV files

Implement a Python standard-library CLI `python3 reconcile.py left.csv right.csv --output result.json`. This is a batch workflow. No browser UI, database, or login is required.

Both CSVs have exactly `id,amount` headers. IDs are nonempty and unique within each file. Amount is a nonnegative finite decimal with at most two fractional digits; scientific notation is invalid. Empty files, wrong headers, malformed rows, duplicate IDs, and invalid amounts are errors.

Output JSON must contain exactly `matched`, `different`, `leftOnly`, `rightOnly`. Arrays are sorted by ID. `matched`, `leftOnly`, and `rightOnly` contain IDs as strings. `different` contains objects with exactly `id`, `left`, `right`; amounts are decimal strings with exactly two fractional digits. Numerically equal inputs like `1` and `1.00` match. Header-only files are valid and produce empty arrays.

Exit 0 on success. On any invalid input, exit nonzero, write a useful message to stderr, and leave any existing output file unchanged. A successful output must be valid as a complete JSON document. Provide run instructions and meaningful executed tests. No review weights are supplied.
