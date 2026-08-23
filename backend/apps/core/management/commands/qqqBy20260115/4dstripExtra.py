import json
from pathlib import Path

base = Path("/Users/williamjames/Documents/CommerceExpert/webclerk3_data")

in_path = base / "4dcatalog_simplified_typed.json"
out_path = base / "4dcatalog_simplified_typed_no_extra.json"

with in_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

def strip_extras(catalog):
    tables = catalog.get("table", [])
    if isinstance(tables, dict):
        tables = [tables]
        catalog["table"] = tables

    for table in tables:
        # remove table_extra if present
        table.pop("table_extra", None)

        fields = table.get("field")
        if not fields:
            continue
        if isinstance(fields, dict):
            fields = [fields]
            table["field"] = fields

        for field in fields:
            # remove field_extra if present
            field.pop("field_extra", None)

strip_extras(data)

with out_path.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Wrote", out_path)
