import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

# 1. Set up the plotting style
sns.set_theme(style="white")
plt.rcParams["font.sans-serif"] = "Arial"
plt.rcParams["font.family"] = "sans-serif"

# 2. Define the exact structure from the image
y_labels = ["20%", "50%", "80%"]
rows_categories = ["all-to-all", "incast"]  # Combined with percentiles

# Column configurations (Subplots matching your image blocks)
columns_data = {
    "allgather bine": ["1KiB", "16KiB", "128KiB", "1MiB", "4MiB", "16MiB"]}


# --- PASTE THIS BLOCK RIGHT BEFORE THE PLOT LOOP ---

my_real_data = {
    "allgather bine": [
        # Must have 9 numbers per row (for MILC, HPCG, LAMMPS, FFT, resnet-proxy, silo, sphinx, xapian, img-dnn)
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],  # all-to-all 20%
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],  # all-to-all 50%
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.1, 1.1],  # all-to-all 80%
        [1.0, 1.0, 1.0, 1.1, 1.0, 1.0, 1.1, 1.1, 1.0],  # incast 20%
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.0],  # incast 50%
        [1.0, 1.2, 1.0, 1.0, 1.0, 1.0, 1.1, 1.0, 1.0],  # incast 80%
    ]
}

# Total combined rows: 3 for all-to-all, 3 for incast
total_rows = 6
y_axis_ticks = ["20%", "50%", "80%", "20%", "50%", "80%"]

# 3. Create the multi-plot grid layout dynamically based on columns
num_plots = len(columns_data)
# Widths are proportional to the number of columns in each block
widths = [len(cols) for cols in columns_data.values()]

fig, axes = plt.subplots(
    nrows=1,
    ncols=num_plots,
    figsize=(16, 4),
    sharey=True,
    gridspec_kw={"width_ratios": widths, "wspace": 0.05},  # Tiny gap like image
)

# Custom dark green colormap similar to your Slingshot image
# Values near 1.0 are dark green; higher values (1.2, 1.5) get lighter
colors = ["#004d26", "#e6f598", "#fdae61", "#a50026"]
ccolor = LinearSegmentedColormap.from_list("custom_green_red", colors, N=256)

# 4. Populate each subplot with dummy data (mostly 1s, occasional 1.1 - 1.5)
#np.random.seed(42)  # For reproducible random mock variations

tutti_i_valori = [
    valore for matrice in my_real_data.values() for riga in matrice for valore in riga
]
vmax1 = max(tutti_i_valori)

for i, (title, cols) in enumerate(columns_data.items()):
    ax = axes[i]

    # Generate baseline data matrix of 1.0s
    data = np.array(my_real_data[title])

    # Draw Heatmap
    sns.heatmap(
        data,
        ax=ax,
        cmap=ccolor,
        cbar=False,  # No colorbar needed
        annot=True,
        fmt=".2g",  # Keeps notation brief (e.g., "1", "1.1")
        annot_kws={"size": 9, "color": "white", "alpha": 0.7, "weight": "bold"},
        linewidths=0.5,
        linecolor="white",
        vmin=1.0,
        vmax=vmax1
    )

    # X-axis adjustments
    ax.set_xticklabels(cols, rotation=90, ha="center", fontsize=10)
    ax.xaxis.tick_bottom()

    # Bottom labels grouping categories (skip for first 'Workloads' block)
    if title != "Workloads":
        ax.set_xlabel(title, fontsize=11, labelpad=10, weight="bold")
    else:
        ax.set_xlabel("", labelpad=10)

    # Draw the middle horizontal line dividing "all-to-all" from "incast"
    ax.axhline(3, color="white", linewidth=2.5)

# 5. Leftmost Y-Axis Labeling Setup
axes[0].set_yticks(np.arange(total_rows) + 0.5)
axes[0].set_yticklabels(y_axis_ticks, rotation=0, fontsize=10)

# Add the multi-level outer text on the far left side
fig.text(
    0.01,
    0.7,
    "Slingshot (Shandy)\nall-to-all",
    va="center",
    ha="right",
    rotation=90,
    fontsize=11,
)
fig.text(
    0.01,
    0.32,
    "incast",
    va="center",
    ha="right",
    rotation=90,
    fontsize=11,
)

# Tight layout settings to match original visualization aspect ratio
plt.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.25)

# Save or show
plt.savefig("slingshot_matrix_heatmap.png", dpi=300)
plt.show()