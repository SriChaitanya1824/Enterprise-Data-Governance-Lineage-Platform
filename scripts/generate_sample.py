"""Create deterministic synthetic banking files; never uses customer information."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data"


def write(path, fields, rows):
    target = ROOT / path
    if "--preserve" in sys.argv and target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    customers = [{"customer_id": f"SYN-C{i:04}", "customer_name": f"Synthetic Customer {i:03}",
                  "country": ["DE", "FR", "GB", "US", "AE"][i % 5],
                  "risk_rating": ["LOW", "MEDIUM", "HIGH"][i % 3]} for i in range(1, 101)]
    raw = [dict(row) for row in customers]
    raw[4]["country"] = "ZZ"
    raw[8]["customer_name"] = ""
    raw[12]["risk_rating"] = "UNKNOWN"
    write("raw/customers.csv", list(customers[0]), raw)
    for name in ["customer_clean", "customer_master", "customer_risk", "credit_risk_dataset", "regulatory_customer_report"]:
        write(f"curated/{name}.csv", list(customers[0]), customers)
    transactions = [{"transaction_id": f"SYN-T{i:05}", "account_id": f"SYN-A{i:04}",
                     "transaction_amount": round(125.50 + i * 13.75, 2), "transaction_date": "2026-10-01"} for i in range(1, 101)]
    dirty = [dict(t) for t in transactions]
    dirty[3]["transaction_amount"] = -25
    dirty[7]["account_id"] = ""
    write("raw/transactions.csv", list(transactions[0]), dirty)
    for name in ["transaction_clean", "regulatory_transaction_report"]:
        write(f"curated/{name}.csv", list(transactions[0]), transactions)
    accounts = [{"account_id": f"SYN-A{i:04}", "customer_id": f"SYN-C{i:04}", "product_type": "CURRENT" if i % 2 else "SAVINGS"} for i in range(1, 101)]
    write("sample/accounts.csv", list(accounts[0]), accounts)
    for filename in ["ledger", "exposures", "positions"]:
        rows = [{"account_id": f"SYN-A{i:04}", "transaction_amount": round(i * 523.75, 2), "business_date": "2026-10-01"} for i in range(1, 101)]
        write(f"sample/{filename}.csv", list(rows[0]), rows)


if __name__ == "__main__":
    main()
