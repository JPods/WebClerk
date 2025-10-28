#!/usr/bin/env python
"""
Import CSV → Action model
Fixed: BOM, timezone.utc, Django shadowing
"""

import csv
import os
import sys
from pathlib import Path
from datetime import datetime, timezone  # timezone.utc from datetime
from typing import List, Dict

# === Django Setup ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webclerk3_api.settings")
import django
django.setup()

# === Models ===
from apps.core.models import Action

# === DO NOT import `from django.utils import timezone` ===
# Use alias to avoid conflict
from django.utils import timezone as dj_timezone  # only for .now()


# === Constants ===
KANBAN_COLUMNS = [
    ('Backlog', 'Backlog'),
    ('Planning', 'Planning'),
    ('InProcess', 'In Process'),
    ('Review', 'Review'),
    ('Complete', 'Complete'),
]
STATUS_TO_KANBAN = {label.lower(): value for value, label in KANBAN_COLUMNS}

DIFFICULTY_LEVELS = [
    (100, 'Extreme'), (50, 'Hard'), (15, 'Moderate'),
    (10, 'Normal'), (4, 'Easy'), (1, 'Trivial'),
]
EFFORT_TO_DIFFICULTY = {label.lower(): value for value, label in DIFFICULTY_LEVELS}


# === Helpers ===
def parse_date(date_str: str):
    if not date_str or not date_str.strip():
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return dt.replace(tzinfo=timezone.utc)  # Correct
    except ValueError as e:
        print(f"Warning: Invalid date '{date_str}': {e}")
        return None


def parse_assignees(assignee_str: str) -> List[Dict[str, str]]:
    if not assignee_str or not assignee_str.strip():
        return []
    names = [n.strip() for n in assignee_str.split(',') if n.strip()]
    return [{"name": n} for n in names]


def map_status_to_kanban(status: str) -> str:
    mapping = {
        'done': 'Complete',
        'not started': 'Backlog',
        'on hold': 'Backlog',
        'in progress': 'InProcess',
        'on review': 'Review',
    }
    return mapping.get(status.strip().lower(), 'Backlog')


def map_effort_to_difficulty(effort: str) -> int:
    return EFFORT_TO_DIFFICULTY.get(effort.strip().lower(), 10)


# === Main Import ===
def import_csv_to_actions(csv_file_path: str):
    if not os.path.exists(csv_file_path):
        print(f"Error: File not found: {csv_file_path}")
        return

    actions_to_create = []

    with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:  # BOM-safe
        reader = csv.DictReader(file)
        # Clean headers
        reader.fieldnames = [field.strip().replace('\ufeff', '') for field in reader.fieldnames]
        print(f"Cleaned CSV columns: {reader.fieldnames}")

        for row in reader:
            task_name = row.get('Task name', '').strip()
            if not task_name:
                continue

            assignee_str = row.get('Assignee', '')
            description = row.get('Description', '') or None
            due_date_str = row.get('Due date', '')
            effort_level = row.get('Effort level', '')
            priority_str = row.get('Priority', '')
            status = row.get('Status', 'Not started')

            action = Action(
                action_en=task_name,
                description_en=description,
                assigned_to=parse_assignees(assignee_str),
                dt_due=parse_date(due_date_str),
                difficulty=map_effort_to_difficulty(effort_level),
                priority=int(priority_str) if priority_str and priority_str.isdigit() else 1,
                kanban_column=map_status_to_kanban(status),
                status=status.strip() or None,
                languages=["en"],
            )
            actions_to_create.append(action)

    print(f"Importing {len(actions_to_create)} actions...")
    Action.objects.bulk_create(actions_to_create, batch_size=100)
    print("Import completed successfully!")


# === Run ===
if __name__ == "__main__":
    CSV_FILE_PATH = '/Users/an7or/Public/Private & Shared/WC3 All 2091d7dbe231803db779e57453d93588_all.csv'
    import_csv_to_actions(CSV_FILE_PATH)