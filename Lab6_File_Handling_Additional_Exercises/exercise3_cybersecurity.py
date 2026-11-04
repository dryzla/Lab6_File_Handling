from pathlib import Path

LAST_NAME = "Villamor"
STUDENT_ID = "TUPM-26-3469"

SEED_DIGIT = int(STUDENT_ID[-1])
ID_SUM = sum(int(d) for d in STUDENT_ID if d.isdigit())
NAME_LENGTH = len(LAST_NAME)

WORK_DIR = Path(".")
DATA_DIR = WORK_DIR / "data" 
OUTPUT_DIR = WORK_DIR / "output"
BACKUP_DIR = WORK_DIR / "backup"

for folder in (DATA_DIR, OUTPUT_DIR, BACKUP_DIR):
    folder.mkdir(exist_ok=True)

print("Student:", LAST_NAME, "|", STUDENT_ID)
print("Seed:", SEED_DIGIT, "| ID Sum:", ID_SUM, "| Name Length:", NAME_LENGTH)
print("Workspace:", WORK_DIR.resolve())

import csv
import filecmp
import json
import math
import shutil
from collections import Counter

CYBER_DATASET = DATA_DIR / "Global_Cybersecurity_Threats_2015-2024.csv"

TARGET_YEAR = 2015 + SEED_DIGIT
LOSS_FIELD = "Financial Loss (in Million $)"
COUNT_FIELD = "Attack Type"

CYBER_FILTERED_CSV = OUTPUT_DIR / f"{LAST_NAME}_{STUDENT_ID}_cyber_{TARGET_YEAR}_filtered.csv"
CYBER_SUMMARY_JSON = OUTPUT_DIR / f"{LAST_NAME}_{STUDENT_ID}_cyber_{TARGET_YEAR}_summary.json"
CYBER_BACKUP_JSON = BACKUP_DIR / CYBER_SUMMARY_JSON.name
CYBER_REPORT_TXT = OUTPUT_DIR / f"{LAST_NAME}_{STUDENT_ID}_cyber_{TARGET_YEAR}_report.txt"

print("Target year:", TARGET_YEAR)

def parse_loss(text):
    """Return a valid financial loss (finite and >= 0) or None if invalid/missing."""
    try:
        value = float(str(text).strip())
    except ValueError:
        return None
    return value if math.isfinite(value) and value >= 0 else None


def analyze_incidents():
    """Stream the dataset once, writing the target-year incidents to a filtered CSV."""
    total_records = selected = invalid_year = invalid_loss = 0
    attack_counts = Counter()
    ranked = []                   
    total_loss = 0.0

    with open(CYBER_DATASET, "r", encoding="utf-8", newline="") as source, \
         open(CYBER_FILTERED_CSV, "w", encoding="utf-8", newline="") as target:

        reader = csv.DictReader(source)
        required = ["Year", COUNT_FIELD, LOSS_FIELD]
        missing = [f for f in required if f not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Dataset is missing required columns: {missing}")

        writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
        writer.writeheader()

        for order, row in enumerate(reader):
            total_records += 1

            try:
                year = int(str(row["Year"]).strip())
            except ValueError:
                invalid_year += 1            
                continue
            if year != TARGET_YEAR:
                continue

            selected += 1
            writer.writerow(row)
            attack_counts[(row[COUNT_FIELD] or "").strip() or "(missing)"] += 1

            loss = parse_loss(row[LOSS_FIELD])
            if loss is None:
                invalid_loss += 1
                continue
            total_loss += loss
            ranked.append((loss, order, row))

    valid_loss_count = len(ranked)
    average_loss = total_loss / valid_loss_count if valid_loss_count else None

    top_five = sorted(ranked, key=lambda item: -item[0])[:5]

    return {
        "total_records": total_records,
        "selected": selected,
        "invalid_year": invalid_year,
        "invalid_loss": invalid_loss,
        "attack_counts": attack_counts,
        "total_loss": total_loss,
        "average_loss": average_loss,
        "top_five": top_five,
    }


try:
    inc = analyze_incidents()
except FileNotFoundError:
    raise SystemExit(f"Dataset not found: {CYBER_DATASET}. Place the CSV inside the data folder.")

if inc["selected"] == 0:
    print(f"No incidents were found for {TARGET_YEAR}.")

print("Total records:", inc["total_records"])
print("Incidents in", TARGET_YEAR, ":", inc["selected"])
print("Invalid financial values skipped:", inc["invalid_loss"])

top_five_records = [
    {
        "rank": rank,
        "financial_loss_million_usd": loss,
        "dataset_row": order + 2,            # +1 for header, +1 for 1-based numbering
        "record": dict(row),
    }
    for rank, (loss, order, row) in enumerate(inc["top_five"], 1)
]

cyber_summary = {
    "student": LAST_NAME,
    "student_id": STUDENT_ID,
    "seed_digit": SEED_DIGIT,
    "target_year": TARGET_YEAR,
    "total_records_in_dataset": inc["total_records"],
    "incidents_in_target_year": inc["selected"],
    "count_per_attack_type": dict(sorted(inc["attack_counts"].items(), key=lambda kv: (-kv[1], kv[0]))),
    "total_financial_loss_million_usd": round(inc["total_loss"], 2),
    "average_financial_loss_million_usd": None if inc["average_loss"] is None else round(inc["average_loss"], 2),
    "invalid_financial_values_skipped": inc["invalid_loss"],
    "five_costliest_incidents": top_five_records,
    "filtered_csv": CYBER_FILTERED_CSV.name,
}

with open(CYBER_SUMMARY_JSON, "w", encoding="utf-8") as file:
    json.dump(cyber_summary, file, indent=4)

shutil.copy2(CYBER_SUMMARY_JSON, CYBER_BACKUP_JSON)
backup_ok = (
    CYBER_BACKUP_JSON.exists()
    and CYBER_BACKUP_JSON.stat().st_size == CYBER_SUMMARY_JSON.stat().st_size
    and filecmp.cmp(CYBER_SUMMARY_JSON, CYBER_BACKUP_JSON, shallow=False)
)

with open(CYBER_FILTERED_CSV, "r", encoding="utf-8", newline="") as file:
    exported_rows = sum(1 for _ in csv.DictReader(file))
csv_ok = exported_rows == inc["selected"]

fmt_money = lambda v: "N/A" if v is None else f"{v:,.2f}"

with open(CYBER_REPORT_TXT, "w", encoding="utf-8") as report:
    report.write("CYBERSECURITY INCIDENT REPORT\n")
    report.write("-" * 60 + "\n")
    report.write(f"Student           : {LAST_NAME} ({STUDENT_ID})\n")
    report.write(f"Target Year       : {TARGET_YEAR}\n")
    report.write(f"Total Records     : {inc['total_records']}\n")
    report.write(f"Incidents ({TARGET_YEAR}) : {inc['selected']}\n\n")

    report.write("INCIDENT COUNT PER ATTACK TYPE\n")
    if inc["attack_counts"]:
        for attack, count in sorted(inc["attack_counts"].items(), key=lambda kv: (-kv[1], kv[0])):
            report.write(f"  {attack:<20} {count}\n")
    else:
        report.write("  No incidents found.\n")

    report.write("\nFINANCIAL LOSSES (USD millions)\n")
    report.write(f"  Total   : {fmt_money(inc['total_loss'] if inc['selected'] else None)}\n")
    report.write(f"  Average : {fmt_money(inc['average_loss'])}\n")
    report.write(f"  Invalid financial values skipped: {inc['invalid_loss']}\n")

    report.write("\nFIVE COSTLIEST INCIDENTS\n")
    if top_five_records:
        for item in top_five_records:
            rec = item["record"]
            report.write(
                f"  {item['rank']}. {rec['Country']} | {rec[COUNT_FIELD]} | {rec['Target Industry']} | "
                f"${item['financial_loss_million_usd']:,.2f}M (row {item['dataset_row']})\n"
            )
    else:
        report.write("  None.\n")

    report.write("\nOUTPUT FILES\n")
    for path in (CYBER_FILTERED_CSV, CYBER_SUMMARY_JSON, CYBER_BACKUP_JSON):
        report.write(f"  {path.name} - {path.stat().st_size} bytes\n")
    report.write(f"  Backup verification: {'VERIFIED' if backup_ok else 'FAILED'}\n")

print("=" * 60)
print("EXERCISE 3: CYBERSECURITY INCIDENT REPORT - ASSESSMENT DATA")
print("=" * 60)
print("Target year                    :", TARGET_YEAR)
print("Total records in dataset       :", inc["total_records"])
print("Incidents in target year       :", inc["selected"])
print("Count per attack type          :", dict(sorted(inc["attack_counts"].items())) or "None")
print("Total financial loss (USD M)   :", round(inc["total_loss"], 2))
print("Average financial loss (USD M) :", None if inc["average_loss"] is None else round(inc["average_loss"], 2))
print("Five costliest incidents:")
for item in top_five_records:
    rec = item["record"]
    print(f"   {item['rank']}. {rec['Country']}, {rec[COUNT_FIELD]}, {rec['Target Industry']}: ${item['financial_loss_million_usd']}M")
print("Filtered CSV file              :", CYBER_FILTERED_CSV, f"({exported_rows} rows, count check: {'OK' if csv_ok else 'MISMATCH'})")
print("JSON summary file              :", CYBER_SUMMARY_JSON)
print("Backup verification            :", CYBER_BACKUP_JSON, "-", "VERIFIED" if backup_ok else "FAILED")
print("Report file                    :", CYBER_REPORT_TXT)
