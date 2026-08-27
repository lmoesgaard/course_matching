# Course Matching (SDU ↔ KU)

Embedding-based cross-university course matching between the University of Southern
Denmark (SDU) and the University of Copenhagen (KU) using sentence embeddings and
cosine similarity. Each course's official description is embedded, normalized, and
compared pairwise so that similar courses across the two universities can be mapped
to one another (e.g. for credit-transfer / crosswalk decisions).

## Dependencies

- Python ≥ 3.12
- `numpy`, `pandas`, `matplotlib`, `sentence-transformers`

## Setup

This project uses [`uv`](https://docs.astral.sh/uv/) for dependency management.
Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`.

```bash
# create / sync the environment and install dependencies
uv sync

# (or, to produce a lockfile from the declared deps without installing)
uv lock
```

## Data

| File | Description |
|------|-------------|
| `data/SDU_KU_Course_Matching.xlsx` | **Input.** 46 course records (25 SDU, 21 KU) with `Course Code`, `Course Title`, `Semester`, `University`, and `Description` |
| `data/course_similarity_long.csv` | **Output.** 525 cross-university course pairs: `course_KU`, `course_SDU`, `Semester`, `similarity` |
| `data/course_similarity_matrix.csv` | **Output.** 46×46 symmetric similarity matrix indexed by course title |

## Pipeline (`embeddings assesment.py`)

1. **Encode** — each course `Description` is embedded with
   `paraphrase-multilingual-MiniLM-L12-v2` (384-d).
2. **Normalize** — embeddings are mean-centered, and optionally **top-k PCA
   whitened** (de-anisotropy) to increase the contrast of the similarity scores.
   The current run uses `whiten=True, top_k=10`.
3. **Pair** — every unordered pair of courses is generated with
   `itertools.combinations`.
4. **Score** — cosine similarity is computed for each pair.
5. **Min-max scale** — similarities are rescaled to `[0, 1]` *before* filtering, so
   the strongest (self) similarity fixes the upper bound at 1.
6. **Emit** — a full similarity matrix is written, and a long-format table is
   built after removing self-comparisons and within-university pairs, keeping only
   cross-university (SDU ↔ KU) pairs.

Run it with:

```bash
uv run "embeddings assesment.py"
```

## Interfaces

- `interfaces/course_match.py` — command-line tool to explore SDU↔KU matches. !!! NOT UP TO DATE !!!
- `interfaces/course_match.html` — interactive HTML explorer. !!! NOT UP TO DATE !!!
- `interfaces/farmaci_crosswalk.html` — interactive bipartite "crosswalk" view:
  SDU courses on top, KU courses below, links weighted by description similarity,
  with filtering and per-course isolation.

## Notes

- Scores reflect how closely two course *descriptions* overlap; they are a prompt for further reading, not a definitive equivalence.
- Danish and English descriptions are embedded by a multilingual model.

## License

N/A
