import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

SIZES       = [1024, 16384, 131072, 1048576, 4194304, 16777216]
SIZE_LABELS = ["1KiB", "16KiB", "128KiB", "1MiB", "4MiB", "16MiB"]
TYPES       = ["linear", "interleaved", "random"]
PERCS       = ["10/90", "20/80", "50/50"]

CMAP = LinearSegmentedColormap.from_list(
    "rg", ["#1a6e2e", "#a6d96a", "#ffffbf", "#fdae61", "#d7191c"]
)

CELL = 0.62   # cell size (square)
SEP  = 0.22   # vertical gap between type blocks
LPAD = 1.30   # left  margin (type + perc labels)
RPAD = 1.00   # right margin (colorbar)
TPAD = 0.55   # top   margin
BPAD = 0.65   # bottom margin (x-axis labels)


def load(path):
    df = pd.read_csv(path)
    df["ratio"] = df["Avg_B"] / df["Avg_A"]
    return df[df["Size"].isin(SIZES) & df["Perc"].isin(PERCS) & df["Type"].isin(TYPES)]


def build_matrix(df):
    index = pd.MultiIndex.from_tuples(
        [(t, p) for t in TYPES for p in PERCS], names=["Type", "Perc"]
    )
    mat = pd.DataFrame(index=index, columns=SIZES, dtype=float)
    for t in TYPES:
        for p in PERCS:
            for s in SIZES:
                sel = df[(df["Type"]==t) & (df["Perc"]==p) & (df["Size"]==s)]
                if not sel.empty:
                    mat.loc[(t, p), s] = sel["ratio"].values[0]
    mat.columns = SIZE_LABELS
    return mat


def plot(df, out):
    mat  = build_matrix(df)
    vmin = float(mat.values.min())
    vmax = float(mat.values.max())

    n_types = len(TYPES)
    block_h = len(PERCS) * CELL
    total_h = n_types * block_h + (n_types - 1) * SEP
    grid_w  = len(SIZE_LABELS) * CELL

    fig_w = LPAD + grid_w + RPAD
    fig_h = TPAD + total_h + BPAD

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    def fx(x): return x / fig_w
    def fy(y): return y / fig_h

    # one axes per type block
    axes = []
    for gi in range(n_types):
        blocks_below = n_types - 1 - gi
        y0 = BPAD + blocks_below * (block_h + SEP)
        ax = fig.add_axes([fx(LPAD), fy(y0), fx(grid_w), fy(block_h)])
        axes.append(ax)

    cbar_ax = fig.add_axes([fx(LPAD + grid_w + 0.18), fy(BPAD), fx(0.22), fy(total_h)])

    for gi, (t, ax) in enumerate(zip(TYPES, axes)):
        sub = mat.loc[t].copy()
        sub.index = PERCS
        is_last  = gi == n_types - 1
        is_first = gi == 0

        sns.heatmap(
            sub.astype(float),
            ax=ax,
            cmap=CMAP,
            vmin=vmin, vmax=vmax,
            annot=True, fmt=".2f",
            annot_kws={"size": 7.5, "weight": "bold"},
            linewidths=0.5, linecolor="white",
            square=True,
            cbar=is_first,
            cbar_ax=cbar_ax if is_first else None,
            xticklabels=is_last,
            yticklabels=True,
        )

        ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=8, rotation=0, length=0)
        ax.tick_params(axis="x", labelsize=8, rotation=35, length=0,
                       labelbottom=is_last)
        ax.set_xlabel("message size" if is_last else "", fontsize=9, labelpad=6)

        # type name to the left, vertically centered
        ax.text(-0.22, 0.5, t,
                transform=ax.transAxes,
                ha="right", va="center",
                fontsize=9, color="#111111")

    cbar_ax.tick_params(labelsize=8)

    fig.suptitle("UEC Allgather Bine — AllToAll",
                 fontsize=10, fontweight="bold",
                 x=fx(LPAD + grid_w / 2), y=0.99,
                 ha="center", transform=fig.transFigure)

    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"saved → {out}")


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "allgather_heatmap.png"
    plot(load(csv_path), out_path)
