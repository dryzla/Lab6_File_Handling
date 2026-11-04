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
import json
import shutil

USER_DATASET = DATA_DIR / "user_behavior_dataset.csv"

TARGET_OS = "Android" if SEED_DIGIT % 2 == 0 else "iOS"    
TARGET_BEHAVIOR_CLASS = (SEED_DIGIT % 5) + 1               

EXPORT_FIELDS = [
    "User ID",
    "Device Model",
    "Operating System",
    "Battery Drain (mAh/day)",
    "Data Usage (MB/day)",
]

USER_EXPORT_CSV = OUTPUT_DIR / f"{LAST_NAME}_{STUDENT_ID}_user_profile.csv"
USER_SUMMARY_JSON = OUTPUT_DIR / f"{LAST_NAME}_{STUDENT_ID}_user_summary.json"
USER_BACKUP_CSV = BACKUP_DIR / USER_EXPORT_CSV.name

print("Target operating system:", TARGET_OS)
print("Target behavior class  :", TARGET_BEHAVIOR_CLASS)

def profile_users():
    """Read the dataset row by row, filter by OS and behavior class,
    accumulate battery/data totals, and export the selected users."""
    total_records = os_matches = selected = invalid = 0
    battery_total = data_total = 0.0

    with open(USER_DATASET, "r", encoding="utf-8", newline="") as source, \
         open(USER_EXPORT_CSV, "w", encoding="utf-8", newline="") as target:

        reader = csv.DictReader(source)
        missing = [f for f in EXPORT_FIELDS + ["User Behavior Class"] if f not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Dataset is missing required columns: {missing}")

        writer = csv.DictWriter(target, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            total_records += 1

            if (row["Operating System"] or "").strip().casefold() != TARGET_OS.casefold():
                continue
            os_matches += 1

            try:
                behavior_class = int(row["User Behavior Class"])
                battery = float(row["Battery Drain (mAh/day)"])
                data_usage = float(row["Data Usage (MB/day)"])
            except (TypeError, ValueError):
                invalid += 1
                continue

            if behavior_class != TARGET_BEHAVIOR_CLASS:
                continue

            selected += 1
            battery_total += battery
            data_total += data_usage
            writer.writerow(row)

    avg_battery = battery_total / selected if selected else None   # no matches -> None
    avg_data = data_total / selected if selected else None

    return {
        "total_records": total_records,
        "os_matches": os_matches,
        "invalid": invalid,
        "selected": selected,
        "avg_battery": avg_battery,
        "avg_data": avg_data,
    }


try:
    stats = profile_users()
except FileNotFoundError:
    raise SystemExit(f"Dataset not found: {USER_DATASET}. Place user_behavior_dataset.csv inside the data folder.")

if stats["selected"] == 0:
    print("No users match the assigned operating system and behavior class.")

fmt = lambda value: "N/A" if value is None else round(value, 2)
print("Total records:", stats["total_records"])
print("Matching OS  :", stats["os_matches"])
print("Selected     :", stats["selected"])
print("Avg battery  :", fmt(stats["avg_battery"]), "mAh/day")
print("Avg data     :", fmt(stats["avg_data"]), "MB/day")

with open(USER_EXPORT_CSV, "r", encoding="utf-8", newline="") as file:
    exported_rows = sum(1 for _ in csv.DictReader(file))
count_verified = exported_rows == stats["selected"]

shutil.copy2(USER_EXPORT_CSV, USER_BACKUP_CSV)
backup_exists = USER_BACKUP_CSV.exists()
backup_size = USER_BACKUP_CSV.stat().st_size if backup_exists else 0
backup_ok = backup_exists and backup_size == USER_EXPORT_CSV.stat().st_size

user_summary = {
    "student": LAST_NAME,
    "student_id": STUDENT_ID,
    "seed_digit": SEED_DIGIT,
    "operating_system": TARGET_OS,
    "user_behavior_class": TARGET_BEHAVIOR_CLASS,
    "total_records_in_dataset": stats["total_records"],
    "records_matching_os": stats["os_matches"],
    "invalid_records_skipped": stats["invalid"],
    "records_in_target_behavior_class": stats["selected"],
    "average_battery_drain_mah_per_day": None if stats["avg_battery"] is None else round(stats["avg_battery"], 2),
    "average_data_usage_mb_per_day": None if stats["avg_data"] is None else round(stats["avg_data"], 2),
    "exported_fields": EXPORT_FIELDS,
    "exported_csv": USER_EXPORT_CSV.name,
    "exported_row_count": exported_rows,
    "row_count_verified": count_verified,
    "backup_file": USER_BACKUP_CSV.name,
    "backup_size_bytes": backup_size,
}

with open(USER_SUMMARY_JSON, "w", encoding="utf-8") as file:
    json.dump(user_summary, file, indent=4)

print("=" * 60)
print("EXERCISE 2: MOBILE DEVICE USAGE PROFILING - ASSESSMENT DATA")
print("=" * 60)
print("Operating system and behavior class:", TARGET_OS, "/ Class", TARGET_BEHAVIOR_CLASS)
print("Total records in dataset           :", stats["total_records"])
print("Records matching operating system  :", stats["os_matches"])
print("Records in target behavior class   :", stats["selected"])
print("Average battery drain (mAh/day)    :", fmt(stats["avg_battery"]))
print("Average data usage (MB/day)        :", fmt(stats["avg_data"]))
print("Count verification                 :", f"{exported_rows} exported = {stats['selected']} selected ->",
      "VERIFIED" if count_verified else "MISMATCH")
print("Exported CSV file                  :", USER_EXPORT_CSV)
print("JSON summary file                  :", USER_SUMMARY_JSON)
print("Backup file and size               :", USER_BACKUP_CSV, f"({backup_size} bytes)",
      "- VERIFIED" if backup_ok else "- FAILED")
