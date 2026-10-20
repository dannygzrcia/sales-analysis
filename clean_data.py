
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sales_data.csv"

df = pd.read_csv(DATA_PATH)

def main():

    original_rows = len(df)
    original_columns = len(df.columns)

    print("Original shape:", df.shape)



    # Remove accidental spaces around column names
    df.columns = df.columns.str.strip()

    # Normalize text without changing identifiers into numbers
    for column in ["Invoice", "StockCode", "Description", "Country"]:
        df[column] = df[column].astype("string").str.strip()

        # Convert empty strings into actual missing values
        df[column] = df[column].replace("", pd.NA)

    # Parse dates; invalid dates become missing and are reported
    df["InvoiceDate"] = pd.to_datetime(
    df["InvoiceDate"],
    format="%m/%d/%y %H:%M",
    errors="coerce"
)

    # Customer IDs are identifiers, not measurements.
    # Nullable integers preserve missing values.
    df["Customer ID"] = pd.to_numeric(
        df["Customer ID"], errors="coerce"
    )

    # Only convert IDs that are whole numbers.
    non_missing_ids = df["Customer ID"].dropna()
    if not non_missing_ids.mod(1).eq(0).all():
        raise ValueError("Customer ID contains non-integer values.")

    df["Customer ID"] = df["Customer ID"].astype("Int64")

    # Ensure transaction measures are numeric
    df["Quantity"] = pd.to_numeric(
        df["Quantity"], errors="coerce"
    )
    df["Price"] = pd.to_numeric(
        df["Price"], errors="coerce"
    )


    # Build a mapping only for stock codes associated with
    # exactly one known, non-missing description.
    known_descriptions = (
        df.dropna(subset=["StockCode", "Description"])
        .groupby("StockCode")["Description"]
        .agg(lambda values: values.unique())
    )

    description_map = {
        stock_code: descriptions[0]
        for stock_code, descriptions in known_descriptions.items()
        if len(descriptions) == 1
    }

    missing_description = df["Description"].isna()

    df.loc[missing_description, "Description"] = (
        df.loc[missing_description, "StockCode"]
        .map(description_map)
    )


    # Record exact duplicates before any rows are removed.
    df["IsExactDuplicate"] = df.duplicated(keep=False)

    # Cancellation invoices commonly have a C prefix.
    df["IsCancellation"] = (
        df["Invoice"]
        .str.upper()
        .str.startswith("C", na=False)
    )

    df["HasMissingCustomerID"] = df["Customer ID"].isna()
    df["HasMissingDescription"] = df["Description"].isna()
    df["HasInvalidInvoiceDate"] = df["InvoiceDate"].isna()

    df["HasNonPositiveQuantity"] = (
        df["Quantity"].le(0).fillna(False)
    )

    df["HasNonPositivePrice"] = (
        df["Price"].le(0).fillna(False)
    )

    # Revenue at the transaction-line level.
    # Negative quantities can represent returns.
    df["LineTotal"] = df["Quantity"] * df["Price"]

    issue_columns = [
        "IsExactDuplicate",
        "IsCancellation",
        "HasMissingCustomerID",
        "HasMissingDescription",
        "HasInvalidInvoiceDate",
        "HasNonPositiveQuantity",
        "HasNonPositivePrice",
    ]

    report_lines = [
        "ONLINE RETAIL DATA CLEANING REPORT",
        "=" * 40,
        f"Original rows: {original_rows}",
        f"Original columns: {original_columns}",
        f"Rows retained: {len(df)}",
        "",
        "Missing values after cleaning:",
        df.isna().sum().to_string(),
        "",
        "Flagged records (counts may overlap):",
    ]

    for column in issue_columns:
        report_lines.append(
            f"{column}: {int(df[column].sum())}"
        )

    report_lines.extend([
        "",
        "Revenue summary (LineTotal):",
        df["LineTotal"].describe().to_string(),
        "",
        "No rows were removed automatically.",
        "Review flagged records before excluding them.",
    ])


if __name__ == "__main__":
    main()
