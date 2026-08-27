#from scipy.constants import alpha
from itertools import combinations

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# Load embedding model
encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")#("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")#
# Load some reports
df = pd.read_excel("data/SDU_KU_Course_Matching.xlsx")
list(df.columns)

# First processing step: drop the bachelor’s-thesis
df = df[~df["Course Title"].str.contains("Bachelor", case=False, na=False)].reset_index(drop=True)


################################# EMBED REASONING #####################################################

# Normalization function: center (and optionally whiten) a list of embedding arrays
def normalize(embeddings, whiten=False, top_k=None):
    # stack into a 2D matrix (rows = courses, cols = embedding dims)
    E = np.stack(embeddings)
    # center: subtract the mean (centroid) vector of the set
    centered = E - E.mean(axis=0)

    if whiten:
        # top-k PCA whitening: keep the top_k principal components only.
        if top_k is None:
            top_k = E.shape[1]   # default = number of embedding dimensions
        _, _, Vt = np.linalg.svd(centered, full_matrices=False)
        k = min(top_k, centered.shape[1], centered.shape[0] - 1)
        proj = centered @ Vt[:k].T
        whitened = proj / proj.std(axis=0, keepdims=True)  # unit variance per component

        # detect degenerate collapse: when k >= n-1 the whitened points form a
        # regular simplex, so every pairwise similarity becomes identical (~0)
        W = whitened / np.linalg.norm(whitened, axis=1, keepdims=True)
        M = W @ W.T
        off = M[~np.eye(M.shape[0], dtype=bool)]
        if off.std() < 1e-3:
            print(f"WARNING: whitening with top_k={k} collapses all pairwise similarities "
                  f"to ~{off.mean():.4f} (identical values). Lower top_k to restore contrast.")
        return [w for w in whitened]

    # just centered, returned as a list of arrays
    return [c for c in centered]

# Embedding and similarity calculation function
def similarity(emb_A, emb_B, method):
    # stack both arrays of embeddings into 2 matrices
    A = np.stack(emb_A); B = np.stack(emb_B)
    # Calculate chosen similarity metric
    if method == "cosine":
       return np.sum(A*B, axis=1) / (np.linalg.norm(A,axis=1) * np.linalg.norm(B,axis=1))
    if method == "dotproduct":
       return np.sum(A*B, axis=1)
    if method == "euclidean":
       return np.sum((A-B)**2, axis=1)
    if method == "manhattan":
       return np.sum(np.abs(A-B), axis=1)
    else:
        print("Please specify which method to use when using the function: cosine, dotproduct, euclidean, or manahattan")


# Min-max scaling: rescale a list of values into [min, max] based on the list's own range
def minmax(arr, min=0, max=1):
    arr = np.array(arr)
    lo, hi = arr.min(), arr.max()
    scaled = (arr - lo) / (hi - lo) * (max - min) + min
    return [float(x) for x in scaled]


# encode the text into embeddings using chosen model
df["embedding"] = normalize(
   list(encoder.encode(list(df["Description"]))),
   whiten=True, top_k=10
)

### Create all possible combinations of course descriptions
# Each element is a (course_title, embedding) tuple
courses = list(zip(df["Course Title"], df["embedding"]))
# Every unique pair of (name, embedding) -> outputs a tuple ((name_a, emb_a), (name_b, emb_b))
pairs = list(combinations(courses, 2))

# Unpack each pair into 4 columns (no dictionaries)
pairs_df = pd.DataFrame(pairs, columns=["course_a", "course_b"])
pairs_df["embedding_a"] = [el[1] for el in pairs_df["course_a"]]
pairs_df["embedding_b"] = [el[1] for el in pairs_df["course_b"]]
pairs_df["course_a"] = [el[0] for el in pairs_df["course_a"]]
pairs_df["course_b"] = [el[0] for el in pairs_df["course_b"]]


### calculate similarity/distance for each pair of course descriptions
pairs_df["similarity"] = similarity(pairs_df["embedding_a"],pairs_df["embedding_b"], "cosine")
# Min-max scale the similarities into [0,1] BEFORE removing self-comparisons,
# so the strongest (self) similarity fixes the upper bound at 1.
pairs_df["similarity"] = minmax(pairs_df["similarity"])


### Make a similarity matrix for all possible pairs of course descriptions
names = df["Course Title"].tolist()
sim_matrix = pd.DataFrame(0.0, index=names, columns=names)

for _, row in pairs_df.iterrows():
    a, b, sim = row["course_a"], row["course_b"], row["similarity"]
    sim_matrix.loc[a, b] = sim
    sim_matrix.loc[b, a] = sim


### Save relevant files
# save similarity matrix to csv
sim_matrix.to_csv("data/course_similarity_matrix.csv")

# remove redundant rows from the pair dataframe:
## 1. self-comparison (course vs itself)
pairs_df = pairs_df[pairs_df["course_a"] != pairs_df["course_b"]].copy()

## 2. Comparison within university (only compare courses across university)
uni = df.set_index("Course Title")["University"]
pairs_df["uni_a"] = pairs_df["course_a"].map(uni)
pairs_df["uni_b"] = pairs_df["course_b"].map(uni)
pairs_df = pairs_df[pairs_df["uni_a"] != pairs_df["uni_b"]].copy()

## 3. Reshape the dataframe to to final usable form
sem = df.set_index("Course Title")["Semester"]
pairs_df["sem_a"] = pairs_df["course_a"].map(sem)
pairs_df["sem_b"] = pairs_df["course_b"].map(sem)

is_ku_a = pairs_df["uni_a"] == "KU"
pairs_df["course_KU"]  = np.where(is_ku_a, pairs_df["course_a"],  pairs_df["course_b"])
pairs_df["course_SDU"] = np.where(is_ku_a, pairs_df["course_b"], pairs_df["course_a"])
pairs_df["Semester_KU"]   = np.where(is_ku_a, pairs_df["sem_a"],    pairs_df["sem_b"])
pairs_df["Semester_SDU"]   = np.where(is_ku_a, pairs_df["sem_b"],    pairs_df["sem_a"])

pairs_df = pairs_df[["course_KU", "course_SDU", "Semester_KU", "Semester_SDU", "similarity"]].copy()
pairs_df = pairs_df.sort_values(["Semester_KU", "course_KU", "similarity"],
                                ascending=[True, True, False]).reset_index(drop=True)
# save pairs_df to csv
pairs_df.to_csv("data/course_similarity_long.csv", index=False)
print(pairs_df.head())
