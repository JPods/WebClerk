"""
CodeMap Architecture API — Layer 3
Returns node mapping data from codemap.json for any node in any flowchart.
Alice and the flight simulator use this to answer architecture questions.

Usage via manage action:
    POST /wcapi/manage/
    { "action": "get_architecture_node", "params": { "node": "pending" } }
    { "action": "get_architecture_map", "params": { "flowchart": "wc3-inventory-buckets" } }
    { "action": "list_architecture_flowcharts", "params": {} }
"""

import json
from pathlib import Path


# codemap.json lives in the Allie readmes — single source of truth
_CODEMAP_PATH = Path.home() / "Allie" / "readmes" / "flowcharts" / "codemap.json"
# Fallback: look in WC3 readmes if Allie is not mounted
_CODEMAP_FALLBACK = Path(__file__).resolve().parents[3] / "readmes" / "flowcharts" / "codemap.json"

# Flowcharts directory
_FLOWCHARTS_DIR = Path.home() / "Allie" / "readmes" / "flowcharts"


def _load_codemap() -> dict:
    """Load the codemap.json mapping file."""
    path = _CODEMAP_PATH if _CODEMAP_PATH.exists() else _CODEMAP_FALLBACK
    if not path.exists():
        raise ValueError(f"codemap.json not found at {_CODEMAP_PATH} or {_CODEMAP_FALLBACK}")
    with open(path) as f:
        return json.load(f)


def get_architecture_node(params: dict) -> dict:
    """Return mapping data for a single node."""
    node_name = params.get("node", "").strip()
    if not node_name:
        raise ValueError("'node' parameter is required")

    codemap = _load_codemap()
    nodes = codemap.get("nodes", {})

    if node_name not in nodes:
        # Fuzzy: check if it's a partial match
        matches = [k for k in nodes if node_name.lower() in k.lower()]
        if not matches:
            raise ValueError(f"Node '{node_name}' not found. Available: {', '.join(sorted(nodes.keys()))}")
        if len(matches) == 1:
            node_name = matches[0]
        else:
            return {
                "matches": matches,
                "message": f"Multiple matches for '{node_name}'. Specify one: {', '.join(matches)}"
            }

    node_data = nodes[node_name]
    base_path = codemap.get("_meta", {}).get("base_path", "")

    return {
        "node": node_name,
        "base_path": base_path,
        **node_data,
    }


def get_architecture_map(params: dict) -> dict:
    """Return all nodes that appear in a specific flowchart's .dot file."""
    flowchart = params.get("flowchart", "").strip()
    if not flowchart:
        raise ValueError("'flowchart' parameter is required (e.g., 'wc3-inventory-buckets')")

    # Find the .dot file
    dot_name = flowchart if flowchart.endswith(".dot") else f"{flowchart}.dot"
    dot_path = _FLOWCHARTS_DIR / dot_name
    if not dot_path.exists():
        available = [f.stem for f in _FLOWCHARTS_DIR.glob("wc3-*.dot") if ".enriched." not in f.name]
        raise ValueError(f"Flowchart '{flowchart}' not found. Available: {', '.join(sorted(available))}")

    dot_content = dot_path.read_text()
    codemap = _load_codemap()
    nodes = codemap.get("nodes", {})

    # Find which mapped nodes appear in this flowchart
    import re
    found = {}
    for node_id, node_data in nodes.items():
        if re.search(rf'\b{node_id}\b\s*\[', dot_content):
            found[node_id] = node_data

    return {
        "flowchart": flowchart,
        "node_count": len(found),
        "nodes": found,
        "base_path": codemap.get("_meta", {}).get("base_path", ""),
    }


def list_architecture_flowcharts(params: dict) -> dict:
    """List all available flowcharts with their node coverage."""
    codemap = _load_codemap()
    nodes = codemap.get("nodes", {})

    import re
    flowcharts = []
    for dot_path in sorted(_FLOWCHARTS_DIR.glob("wc3-*.dot")):
        if ".enriched." in dot_path.name:
            continue
        content = dot_path.read_text()
        mapped = sum(1 for nid in nodes if re.search(rf'\b{nid}\b\s*\[', content))
        # Count total nodes in dot file
        total = len(re.findall(r'^\s+\w+\s*\[', content, re.MULTILINE))
        flowcharts.append({
            "name": dot_path.stem,
            "total_nodes": total,
            "mapped_nodes": mapped,
            "coverage": f"{mapped}/{total}" if total > 0 else "0/0",
            "has_svg": dot_path.with_name(dot_path.stem + ".enriched.svg").exists(),
        })

    return {
        "flowchart_count": len(flowcharts),
        "total_mapped_nodes": len(nodes),
        "flowcharts": flowcharts,
    }


def get_architecture_svg(params: dict) -> dict:
    """Return the enriched SVG content for a flowchart."""
    flowchart = params.get("flowchart", "").strip()
    if not flowchart:
        raise ValueError("'flowchart' parameter is required (e.g., 'wc3-inventory-buckets')")

    svg_name = f"{flowchart}.enriched.svg"
    svg_path = _FLOWCHARTS_DIR / svg_name
    if not svg_path.exists():
        # Try without enriched suffix
        svg_path = _FLOWCHARTS_DIR / f"{flowchart}.svg"
    if not svg_path.exists():
        available = [f.stem.replace(".enriched", "") for f in _FLOWCHARTS_DIR.glob("*.enriched.svg")]
        raise ValueError(f"SVG for '{flowchart}' not found. Available: {', '.join(sorted(set(available)))}")

    return {
        "flowchart": flowchart,
        "svg": svg_path.read_text(),
    }
