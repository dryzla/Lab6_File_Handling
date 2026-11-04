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
import re
import shutil
from collections import Counter

WEBLOG_PATH = DATA_DIR / "weblog.csv"
RECORDS_TO_PROCESS = 1000 + ID_SUM          # first 1000 + ID_SUM data records
TARGET_CLASS = (SEED_DIGIT % 4) + 2         # 2 -> 2xx, 3 -> 3xx, 4 -> 4xx, 5 -> 5xx
TARGET_LABEL = f"{TARGET_CLASS}xx"

FILTERED_CSV = OUTPUT_DIR / f"{LAST_NAME}_{STUDENT_ID}_weblog_filtered.csv"
SUMMARY_JSON = OUTPUT_DIR / f"{LAST_NAME}_{STUDENT_ID}_weblog_summary.json"
BACKUP_JSON = BACKUP_DIR / SUMMARY_JSON.name
IPV4_PATTERN = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

print("Records to process:", RECORDS_TO_PROCESS)
print("Target status class:", TARGET_LABEL)

def parse_record(row):
    """Validate one CSV row of the web log.

    Returns (ip, timestamp, url, status_code, requested_path),
    or None when the record is invalid or malformed.
    """
    if len(row) != 4:                                   # missing / extra fields
        return None

    ip, timestamp, url, status = (field.strip() for field in row)

    if not IPV4_PATTERN.match(ip) or not all(int(p) <= 255 for p in ip.split(".")):
        return None
    if not timestamp or not url:
        return None

    if not (status.isdigit() and len(status) == 3 and status[0] in "12345"):
        return None

    parts = url.split()                                 # e.g. "GET /login.php HTTP/1.1"
    requested_path = parts[1] if len(parts) >= 2 else parts[0]

    return ip, timestamp, url, int(status), requested_path


def analyze_weblog():
    """Stream the log line by line; never load the whole dataset into memory."""
    processed = valid = invalid = selected = 0
    status_counts_all = Counter()        # every valid record that was processed
    status_counts_target = Counter()     # only the target class
    url_counts_target = Counter()        # requested URLs inside the target class

    with open(WEBLOG_PATH, "r", encoding="utf-8", newline="") as source, \
         open(FILTERED_CSV, "w", encoding="utf-8", newline="") as target:

        reader = csv.reader(source)      # lazy: yields one row at a time
        writer = csv.writer(target)

        header = next(reader, None)
        if header is None:
            raise ValueError("The dataset is empty.")
        writer.writerow(header)          # keep the dataset's own column names

        for row in reader:
            if processed >= RECORDS_TO_PROCESS:
                break
            processed += 1

            record = parse_record(row)
            if record is None:
                invalid += 1
                continue

            ip, timestamp, url, status, path = record
            valid += 1
            status_counts_all[status] += 1

            if status // 100 == TARGET_CLASS:
                selected += 1
                status_counts_target[status] += 1
                url_counts_target[path] += 1
                writer.writerow([ip, timestamp, url, status])

    return {
        "header": header,
        "processed": processed,
        "valid": valid,
        "invalid": invalid,
        "selected": selected,
        "status_counts_all": status_counts_all,
        "status_counts_target": status_counts_target,
        "top_urls": url_counts_target.most_common(5),
    }


try:
    result = analyze_weblog()
except FileNotFoundError:
    raise SystemExit(f"Dataset not found: {WEBLOG_PATH}. Place weblog.csv inside the data folder.")

if result["processed"] < RECORDS_TO_PROCESS:
    print(f"Warning: the file has only {result['processed']} data records.")
if result["selected"] == 0:
    print(f"No records belong to the {TARGET_LABEL} class in the processed records.")

print("Records processed:", result["processed"])
print("Valid / invalid:", result["valid"], "/", result["invalid"])
print("Records in target class:", result["selected"])

summary = {
    "student": LAST_NAME,
    "student_id": STUDENT_ID,
    "seed_digit": SEED_DIGIT,
    "id_sum": ID_SUM,
    "records_processed": result["processed"],
    "valid_records": result["valid"],
    "invalid_records_skipped": result["invalid"],
    "target_status_class": TARGET_LABEL,
    "records_in_target_class": result["selected"],
    "count_per_status_code": {str(k): v for k, v in sorted(result["status_counts_target"].items())},
    "count_per_status_code_all_processed": {str(k): v for k, v in sorted(result["status_counts_all"].items())},
    "five_most_requested_urls": [{"url": u, "count": c} for u, c in result["top_urls"]],
    "filtered_csv": FILTERED_CSV.name,
}

with open(SUMMARY_JSON, "w", encoding="utf-8") as file:
    json.dump(summary, file, indent=4)

shutil.copy2(SUMMARY_JSON, BACKUP_JSON)

backup_ok = (
    BACKUP_JSON.exists()
    and BACKUP_JSON.stat().st_size == SUMMARY_JSON.stat().st_size
    and filecmp.cmp(SUMMARY_JSON, BACKUP_JSON, shallow=False)
)

with open(FILTERED_CSV, "r", encoding="utf-8", newline="") as file:
    exported_rows = sum(1 for _ in csv.reader(file)) - 1      # minus header
csv_ok = exported_rows == result["selected"]

print("=" * 60)
print("EXERCISE 1: WEB SERVER ACCESS LOG ANALYSIS - ASSESSMENT DATA")
print("=" * 60)
print("Records processed      :", result["processed"])
print("Target status class    :", TARGET_LABEL)
print("Records in target class:", result["selected"])
print("Count per status code  :", dict(sorted(result["status_counts_target"].items())) or "None")
print("Five most requested URLs:")
if result["top_urls"]:
    for rank, (url, count) in enumerate(result["top_urls"], 1):
        print(f"   {rank}. {url} ({count})")
else:
    print("   None")
print("Filtered CSV file      :", FILTERED_CSV, f"({exported_rows} rows, count check: {'OK' if csv_ok else 'MISMATCH'})")
print("JSON summary file      :", SUMMARY_JSON)
print("Backup verification    :", BACKUP_JSON, "-", "VERIFIED" if backup_ok else "FAILED")