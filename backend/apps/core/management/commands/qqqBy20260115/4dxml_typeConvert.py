import json
from pathlib import Path

base = Path("/Users/williamjames/Documents/CommerceExpert/webclerk3_data")

with (base / "catalog_simplified.json").open("r", encoding="utf-8") as f:
    catalog = json.load(f)

with (base / "4dTypes.json").open("r", encoding="utf-8") as f:
    type_map_raw = json.load(f)

# Invert the 4D map: number (as string) -> type name
# 4dTypes.json is like {"Is real": 1, "Is text": 2, ...} so we build {"1": "Is real", "2": "Is text", ...}
value_to_name = {str(v): k for k, v in type_map_raw.items()}

def patch_field_types(cat):
    tables = cat.get("table", [])
    if isinstance(tables, dict):
        tables = [tables]

    for table in tables:
        fields = table.get("field")
        if not fields:
            continue
        if isinstance(fields, dict):
            fields = [fields]
            table["field"] = fields  # normalize

        for field in fields:
            t = field.get("@type")
            if t is None:
                continue
            # look up the human-readable name by numeric code
            name = value_to_name.get(str(t))
            if name:
                field["@type"] = name

patch_field_types(catalog)

out_path = base / "catalog_simplified_typed.json"
with out_path.open("w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

print("Wrote", out_path)
