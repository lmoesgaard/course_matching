#!/usr/bin/env python
"""Re-embed the latest similarity data into interfaces/farmaci_crosswalk.html.

Usage (run from the repo root, after regenerating the data file):

    uv run python update_crosswalk_html.py

This reads data/course_similarity_long.csv (produced by
"embeddings assesment.py"), maps each pair onto the course nodes already present
in the HTML (so ids / names / semesters are preserved), and rewrites the
embedded JSON (links + max/min) inside the page.
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
HTML_PATH = ROOT / "interfaces" / "farmaci_crosswalk.html"
DATA_PATH = ROOT / "data" / "course_similarity_long.csv"

DATA_TAG = re.compile(
    r'(<script type="application/json" id="data">)(.*?)(</script>)', re.S
)


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    m = DATA_TAG.search(html)
    if not m:
        raise SystemExit(f"Could not find the data JSON block in {HTML_PATH}")

    # Keep the existing node arrays (ids, names, semesters) untouched.
    current = json.loads(m.group(2))
    sdu, ku = current["sdu"], current["ku"]
    name2id = {n["name"]: n["id"] for n in sdu + ku}

    data = pd.read_csv(DATA_PATH)
    links, missing = [], set()
    for _, row in data.iterrows():
        s_id = name2id.get(row["course_SDU"])
        k_id = name2id.get(row["course_KU"])
        if s_id is None:
            missing.add(("SDU", row["course_SDU"]))
        if k_id is None:
            missing.add(("KU", row["course_KU"]))
        links.append(
            {"s": s_id, "k": k_id, "v": round(float(row["similarity"]), 4)}
        )

    if missing:
        print("WARNING: these course names did not match any HTML node (ignored):")
        for side, name in sorted(missing):
            print(f"  {side}: {name}")

    new_json = {
        "sdu": sdu,
        "ku": ku,
        "links": links,
        "max": round(float(data["similarity"].max()), 4),
        "min": round(float(data["similarity"].min()), 4),
    }

    updated = html[:m.start(2)] + json.dumps(new_json, ensure_ascii=False, separators=(",", ":")) + html[m.end(2):]
    HTML_PATH.write_text(updated, encoding="utf-8")

    print(f"Updated {HTML_PATH.name}")
    print(f"  {len(links)} links  (max={new_json['max']}, min={new_json['min']})")


if __name__ == "__main__":
    main()
