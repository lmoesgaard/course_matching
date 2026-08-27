#!/usr/bin/env python3
"""CLI for exploring SDU <-> KU course similarity matches.

Data source: course_similarity_long_named.csv, which contains every
SDU-course x KU-course pair with a similarity score. SDU courses are only
ever compared against KU courses (and vice versa) -- there are no
same-university pairs in this dataset.
"""
import argparse
import csv
import difflib
import sys
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "course_similarity_long_named.csv"


def load_pairs():
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["Similarity Score"] = float(row["Similarity Score"])
    return rows


def course_sets(pairs):
    sdu = sorted({row["SDU Course"] for row in pairs})
    ku = sorted({row["KU Course"] for row in pairs})
    return sdu, ku


def resolve_course(query, sdu_courses, ku_courses):
    """Find which university a course name belongs to and its canonical name.

    Returns (university, canonical_name) or (None, candidates) if the query
    is ambiguous or not found, where candidates is a list of suggestions.
    """
    query_lower = query.strip().lower()

    def exact(courses):
        for c in courses:
            if c.lower() == query_lower:
                return c
        return None

    sdu_hit = exact(sdu_courses)
    ku_hit = exact(ku_courses)
    if sdu_hit and not ku_hit:
        return "SDU", sdu_hit
    if ku_hit and not sdu_hit:
        return "KU", ku_hit
    if sdu_hit and ku_hit:
        return None, [f"{sdu_hit} (SDU)", f"{ku_hit} (KU)"]

    def substring(courses):
        return [c for c in courses if query_lower in c.lower()]

    sdu_matches = substring(sdu_courses)
    ku_matches = substring(ku_courses)
    total = len(sdu_matches) + len(ku_matches)
    if total == 1:
        if sdu_matches:
            return "SDU", sdu_matches[0]
        return "KU", ku_matches[0]
    if total > 1:
        candidates = [f"{c} (SDU)" for c in sdu_matches] + [f"{c} (KU)" for c in ku_matches]
        return None, candidates

    close = difflib.get_close_matches(
        query, sdu_courses + ku_courses, n=5, cutoff=0.4
    )
    if close:
        candidates = [
            f"{c} (SDU)" if c in sdu_courses else f"{c} (KU)" for c in close
        ]
        return None, candidates

    return None, []


def cmd_match(args, pairs, sdu_courses, ku_courses):
    university, resolved = resolve_course(args.course, sdu_courses, ku_courses)
    if university is None:
        if resolved:
            print(f"No exact match for '{args.course}'. Did you mean:")
            for c in resolved:
                print(f"  - {c}")
        else:
            print(f"No course found matching '{args.course}'.")
        return 1

    if university == "SDU":
        key, other_key, other_label = "SDU Course", "KU Course", "KU"
    else:
        key, other_key, other_label = "KU Course", "SDU Course", "SDU"

    matches = sorted(
        (row for row in pairs if row[key] == resolved),
        key=lambda r: r["Similarity Score"],
        reverse=True,
    )[: args.top]

    print(f"Course: {resolved} ({university})")
    print(f"Top {len(matches)} similar {other_label} courses:\n")
    name_width = max((len(m[other_key]) for m in matches), default=0)
    for i, m in enumerate(matches, 1):
        print(f"{i:>2}. {m[other_key]:<{name_width}}  {m['Similarity Score']:.4f}")
    return 0


def cmd_table(args, pairs, sdu_courses, ku_courses):
    ranked = sorted(pairs, key=lambda r: r["Similarity Score"], reverse=True)
    if args.top:
        ranked = ranked[: args.top]

    sdu_width = max((len(r["SDU Course"]) for r in ranked), default=len("SDU Course"))
    ku_width = max((len(r["KU Course"]) for r in ranked), default=len("KU Course"))

    header = f"{'SDU Course':<{sdu_width}}  {'KU Course':<{ku_width}}  Score"
    print(header)
    print("-" * len(header))
    for r in ranked:
        print(
            f"{r['SDU Course']:<{sdu_width}}  {r['KU Course']:<{ku_width}}  {r['Similarity Score']:.4f}"
        )
    return 0


def cmd_list(args, pairs, sdu_courses, ku_courses):
    if args.university in (None, "sdu"):
        print("SDU courses:")
        for c in sdu_courses:
            print(f"  - {c}")
    if args.university in (None, "ku"):
        print("KU courses:")
        for c in ku_courses:
            print(f"  - {c}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Explore similarity between SDU and KU courses."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_match = sub.add_parser(
        "match", help="Find the most similar courses from the opposing university."
    )
    p_match.add_argument("course", help="Course name (SDU or KU), full or partial.")
    p_match.add_argument(
        "-n", "--top", type=int, default=5, help="Number of matches to show (default: 5)."
    )
    p_match.set_defaults(func=cmd_match)

    p_table = sub.add_parser(
        "table", help="Show all SDU-KU course pairs ranked by similarity score."
    )
    p_table.add_argument(
        "-n",
        "--top",
        type=int,
        default=None,
        help="Limit to the top N pairs overall (default: show all).",
    )
    p_table.set_defaults(func=cmd_table)

    p_list = sub.add_parser("list", help="List available course names.")
    p_list.add_argument(
        "-u",
        "--university",
        choices=["sdu", "ku"],
        default=None,
        help="Restrict listing to one university (default: both).",
    )
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    pairs = load_pairs()
    sdu_courses, ku_courses = course_sets(pairs)
    return args.func(args, pairs, sdu_courses, ku_courses)


if __name__ == "__main__":
    sys.exit(main())
