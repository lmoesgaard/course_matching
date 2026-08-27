#!/usr/bin/env python
"""Re-embed the latest similarity data into interfaces/farmaci_crosswalk.html.

Usage (run from the repo root, after regenerating the data file):

    uv run python "02. update_crosswalk_html.py"

This reads ONLY data/course_similarity_long.csv and rebuilds both the course
node lists and the links inside the HTML:

  columns : course_KU, course_SDU, Semester_KU, Semester_SDU, similarity
  - KU  nodes are derived from the unique `course_KU`   values (+ Semester_KU)
  - SDU nodes are derived from the unique `course_SDU`  values (+ Semester_SDU)
  - links map each (SDU, KU) pair with its `similarity` as the edge value

Node ids are assigned sequentially (S0.., K0..) after sorting each side by
semester then name, so nodes adapt automatically when courses are added or
removed in the source data.
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


def _build_nodes(data: pd.DataFrame, side: str) -> list:
    """Return [{id, name, sem, side}] for one university, from the CSV only."""
    if side == "SDU":
        name_col, sem_col, prefix = "course_SDU", "Semester_SDU", "S"
    else:
        name_col, sem_col, prefix = "course_KU", "Semester_KU", "K"

    sub = data[[name_col, sem_col]].drop_duplicates(name_col)
    sub = sub.sort_values([sem_col, name_col]).reset_index(drop=True)

    nodes = []
    for i, row in sub.iterrows():
        nodes.append(
            {
                "id": f"{prefix}{i}",
                "name": row[name_col],
                "sem": int(row[sem_col]),
                "side": side,
            }
        )
    return nodes


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    m = DATA_TAG.search(html)
    if not m:
        raise SystemExit(f"Could not find the data JSON block in {HTML_PATH}")

    data = pd.read_csv(DATA_PATH)
    for col in ("course_KU", "course_SDU", "Semester_KU", "Semester_SDU", "similarity"):
        if col not in data.columns:
            raise SystemExit(f"Missing expected column '{col}' in {DATA_PATH}")

    # Rebuild the node lists purely from the CSV.
    sdu = _build_nodes(data, "SDU")
    ku = _build_nodes(data, "KU")
    name2id = {n["name"]: n["id"] for n in sdu + ku}

    links = [
        {
            "s": name2id[row["course_SDU"]],
            "k": name2id[row["course_KU"]],
            "v": round(float(row["similarity"]), 4),
        }
        for _, row in data.iterrows()
    ]

    new_json = {
        "sdu": sdu,
        "ku": ku,
        "links": links,
        "max": round(float(data["similarity"].max()), 4),
        "min": round(float(data["similarity"].min()), 4),
    }

    updated = (
        html[: m.start(2)]
        + json.dumps(new_json, ensure_ascii=False, separators=(",", ":"))
        + html[m.end(2) :]
    )
    HTML_PATH.write_text(updated, encoding="utf-8")

    print(f"Updated {HTML_PATH.name}")
    print(
        f"  {len(sdu)} SDU nodes, {len(ku)} KU nodes, "
        f"{len(links)} links  (max={new_json['max']}, min={new_json['min']})"
    )


if __name__ == "__main__":
    main()
