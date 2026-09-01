#!/usr/bin/env python3
"""
Plot allgather simulation-time comparison for Dragonfly+ (log/dfp), normalized
to the "bine" algorithm.

Identical to plot_dfp_allgather_times.py, except bar heights are divided by
that same size group's "bine" time before plotting - so within each group
(large/medium/small) bine's bar is always 1.00x tall, and the other
algorithms' bar heights show how many times slower (or faster) they are
relative to bine in that same group. The number printed above each bar is
still the actual simulation time in microseconds (not the ratio) - only the
bar height/y-axis position is normalized.

Reads every "allgather_{algo}_{nodes}n_1024c_1MiB.csv" file in the input
directory (default: ../log/dfp) and takes the total simulation time from the
first line of each file, e.g.:

    # Total Simulation Time: 59.7088

The node count in the filename determines which size group the run belongs
to:
    1332 nodes -> large
    1100 nodes -> medium
    1267 nodes -> small

Produces a grouped bar chart: one x-axis cluster per size group (large,
medium, small), with one bar per collective algorithm (bine, sparbit, bruck,
recdub, ring) inside each cluster, and time relative to bine (x) on the
y-axis.

Usage:
    python3 plot_dfp_allgather_times_normalized.py [--input-dir DIR] [--output FILE]
    python3 plot_dfp_allgather_times_normalized.py --colors "#2a78d6,#1baf7a,#eda100,#008300,#4a3aa7"
"""

import argparse
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")  # non-interactive backend, works fine on server/SSH
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# Filenames look like: allgather_bine_1332n_1024c_1MiB.csv
FILENAME_RE = re.compile(r"^allgather_([a-zA-Z0-9]+)_(\d+)n_1024c_1MiB\.csv$")

# First line looks like: "# Total Simulation Time: 59.7088 " (value is in microseconds).
TIME_RE = re.compile(r"Total Simulation Time:\s*([0-9]*\.?[0-9]+)")

# Node count -> size group, as specified.
NODES_TO_GROUP = {
    1332: "large",
    1100: "medium",
    1267: "small",
}

GROUP_ORDER = ["large", "medium", "small"]

# Fixed algorithm order. Every group's values are normalized against this one.
BASELINE_ALGO = "bine"
ALGO_ORDER = ["bine", "sparbit", "bruck", "recdub", "ring"]

# --- Edit these hex colors to change the palette (order matches ALGO_ORDER). ---
# Can also be overridden per-run with --colors, without touching this file.
PALETTE = [
    "#2a78d6",  # bine
    "#1baf7a",  # sparbit
    "#eda100",  # bruck
    "#008300",  # recdub
    "#4a3aa7",  # ring
]

# --- Font used for every piece of text on the chart. ---
FONT_FAMILY = "Montserrat"
FONT_SIZE = 25  # minimum allowed size - keep at or above 25

# All text on the chart is black; these are only for non-text chrome.
COLOR_TEXT = "#60605F"
COLOR_SURFACE = "#fcfcfb"
COLOR_PAGE = "#f9f9f7"
COLOR_GRIDLINE = "#e1e0d9"
COLOR_BASELINE = "#c3c2b7"

# When two adjacent bars in the same group have close values, their tip labels
# would otherwise overlap - stagger the later one further above its bar.
LABEL_BASE_OFFSET_PT = 3
LABEL_STAGGER_OFFSET_PT = LABEL_BASE_OFFSET_PT + FONT_SIZE * 1.1
LABEL_STAGGER_THRESHOLD_FRAC = 0.02  # fraction of the max value in the dataset


def configure_font(font_family, font_path=None, font_bold_path=None):
    """Register/select the font used for all chart text (regular + bold)."""
    if font_path:
        fm.fontManager.addfont(font_path)
        font_family = fm.FontProperties(fname=font_path).get_name()
    if font_bold_path:
        fm.fontManager.addfont(font_bold_path)

    available = {f.name for f in fm.fontManager.ttflist}
    if font_family not in available:
        print(
            f"Warning: font {font_family!r} was not found on this system - matplotlib "
            f"will fall back to its default font. Install {font_family!r} (or pass "
            f"--font-path to a local .ttf/.otf file) to actually render it.",
            file=sys.stderr,
        )

    bold_file = fm.findfont(fm.FontProperties(family=font_family, weight="bold"))
    if fm.FontProperties(fname=bold_file).get_name() != font_family:
        print(
            f"Warning: no bold variant of {font_family!r} is registered - bold text "
            f"will render as the regular weight. Pass --font-bold-path to a real bold "
            f".ttf/.otf for {font_family!r}.",
            file=sys.stderr,
        )

    plt.rcParams["font.family"] = font_family
    return font_family


def read_total_simulation_time(filepath):
    """Return the total simulation time (float, microseconds) from a file's first line."""
    with open(filepath, "r") as f:
        first_line = f.readline()
    m = TIME_RE.search(first_line)
    if not m:
        raise ValueError(
            f"Could not find 'Total Simulation Time' in first line of {filepath!r}: "
            f"{first_line!r}"
        )
    return float(m.group(1))


def collect_data(input_dir):
    """
    Scan input_dir and return:
        { group: { algo: time_microseconds, ... }, ... }
    """
    data = {group: {} for group in GROUP_ORDER}

    for fname in sorted(os.listdir(input_dir)):
        m = FILENAME_RE.match(fname)
        if not m:
            continue

        algo, nodes_str = m.group(1), m.group(2)
        nodes = int(nodes_str)

        group = NODES_TO_GROUP.get(nodes)
        if group is None:
            print(
                f"Warning: {fname!r} has node count {nodes}, which is not mapped "
                f"to a size group (expected 1332/1100/1267) - skipping.",
                file=sys.stderr,
            )
            continue

        if algo not in ALGO_ORDER:
            print(
                f"Warning: {fname!r} has unrecognized algorithm {algo!r} - skipping.",
                file=sys.stderr,
            )
            continue

        filepath = os.path.join(input_dir, fname)
        try:
            data[group][algo] = read_total_simulation_time(filepath)
        except ValueError as e:
            print(f"Warning: {e} - skipping.", file=sys.stderr)

    return data


def normalize_to_baseline(data):
    """
    Divide every value in each group by that same group's BASELINE_ALGO value,
    so the baseline is always 1.00x within its own group. Groups missing the
    baseline value are dropped (with a warning) since they can't be normalized.
    """
    normalized = {}
    for group in GROUP_ORDER:
        group_data = data.get(group, {})
        baseline = group_data.get(BASELINE_ALGO)
        if baseline is None or baseline == 0:
            if group_data:
                print(
                    f"Warning: group {group!r} has no usable {BASELINE_ALGO!r} value - "
                    f"skipping normalization for this group.",
                    file=sys.stderr,
                )
            normalized[group] = {}
            continue
        normalized[group] = {algo: value / baseline for algo, value in group_data.items()}

    return normalized


def compute_label_offsets(data):
    """
    Return { (group, algo): offset_points }.

    Adjacent bars within a group whose values are close enough that their tip
    labels would collide get the later one pushed further above its bar.
    """
    all_values = [v for group in data.values() for v in group.values()]
    threshold = (max(all_values) if all_values else 0) * LABEL_STAGGER_THRESHOLD_FRAC

    offsets = {}
    for group in GROUP_ORDER:
        prev_height = None
        for algo in ALGO_ORDER:
            value = data.get(group, {}).get(algo)
            if value is None:
                prev_height = None
                continue
            if prev_height is not None and abs(value - prev_height) < threshold:
                offsets[(group, algo)] = LABEL_STAGGER_OFFSET_PT
            else:
                offsets[(group, algo)] = LABEL_BASE_OFFSET_PT
            prev_height = value

    return offsets


def plot_data(normalized_data, raw_data, output_path, algo_colors):
    n_algos = len(ALGO_ORDER)
    n_groups = len(GROUP_ORDER)

    bar_width = 0.8 / n_algos
    group_centers = list(range(n_groups))
    # Bar heights are normalized, but overlap-avoidance follows the same
    # (normalized) visual heights the labels actually sit on top of.
    label_offsets = compute_label_offsets(normalized_data)

    # Font size is large (>=25pt) by request, so give the chart plenty of room.
    fig, ax = plt.subplots(figsize=(22, 14))
    fig.patch.set_facecolor(COLOR_PAGE)
    ax.set_facecolor(COLOR_SURFACE)

    any_missing = False

    for i, algo in enumerate(ALGO_ORDER):
        offset = (i - (n_algos - 1) / 2) * bar_width
        xs = [c + offset for c in group_centers]
        heights = []
        for group in GROUP_ORDER:
            value = normalized_data.get(group, {}).get(algo)
            if value is None:
                any_missing = True
            heights.append(value if value is not None else 0)

        bars = ax.bar(
            xs,
            heights,
            width=bar_width * 0.92,  # small surface gap between adjacent bars
            color=algo_colors[algo],
            label=algo,
            zorder=3,
        )

        # Direct labels at the tip of each bar: the actual simulation time (us),
        # even though the bar height itself is normalized to bine.
        for group, bar, value in zip(GROUP_ORDER, bars, [normalized_data.get(g, {}).get(algo) for g in GROUP_ORDER]):
            if value is None:
                continue
            raw_value = raw_data.get(group, {}).get(algo)
            ax.annotate(
                f"{raw_value:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, label_offsets[(group, algo)]),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=FONT_SIZE,
                fontweight="bold",
                color=COLOR_TEXT,
            )

    if any_missing:
        print(
            "Warning: at least one (group, algorithm) combination had no data "
            "and was plotted as 0.",
            file=sys.stderr,
        )

    ax.set_xticks(group_centers)
    ax.set_xticklabels(
        [g.capitalize() for g in GROUP_ORDER],
        fontsize=FONT_SIZE,
        fontweight="bold",
        color=COLOR_TEXT,
    )

    ax.set_ylabel(
        f"Simulation time relative to {BASELINE_ALGO}",
        fontsize=FONT_SIZE,
        fontweight="bold",
        color=COLOR_TEXT,
    )

    ax.tick_params(axis="y", colors=COLOR_TEXT, labelsize=FONT_SIZE)
    ax.tick_params(axis="x", length=0)
    plt.setp(ax.get_yticklabels(), fontweight="bold")

    ax.yaxis.grid(True, color=COLOR_GRIDLINE, linewidth=1, zorder=0)
    ax.set_axisbelow(True)

    for spine_name, spine in ax.spines.items():
        if spine_name == "bottom":
            spine.set_color(COLOR_BASELINE)
        else:
            spine.set_visible(False)

    legend = ax.legend(
        title="Algorithm",
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        fontsize=FONT_SIZE,
    )
    legend.get_title().set_color(COLOR_TEXT)
    legend.get_title().set_fontsize(FONT_SIZE)
    legend.get_title().set_fontweight("bold")
    for text in legend.get_texts():
        text.set_color(COLOR_TEXT)
        text.set_fontweight("bold")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
    print(f"Saved plot to {output_path}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_input_dir = os.path.join(script_dir, "..", "log", "dfp")
    default_output = os.path.join(
        default_input_dir, "plot", "allgather_simulation_times_normalized.png"
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        default=default_input_dir,
        help=f"Directory containing the allgather_*.csv files (default: {default_input_dir})",
    )
    parser.add_argument(
        "--output",
        default=default_output,
        help=f"Output image path (default: {default_output})",
    )
    parser.add_argument(
        "--colors",
        default=None,
        help=(
            "Comma-separated list of 5 hex colors, one per algorithm in the order "
            f"{ALGO_ORDER} (default: edit the PALETTE constant at the top of this file)."
        ),
    )
    parser.add_argument(
        "--font-family",
        default=FONT_FAMILY,
        help=f"Font family for all chart text (default: {FONT_FAMILY!r}).",
    )
    parser.add_argument(
        "--font-path",
        default=None,
        help="Path to a local .ttf/.otf font file (regular weight) to use if the font family isn't installed system-wide.",
    )
    parser.add_argument(
        "--font-bold-path",
        default=None,
        help="Path to a local .ttf/.otf font file (bold weight) - all chart text is rendered bold.",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"Error: input directory {args.input_dir!r} does not exist.", file=sys.stderr)
        sys.exit(1)

    data = collect_data(args.input_dir)

    if not any(data[g] for g in GROUP_ORDER):
        print(f"Error: no matching data files found in {args.input_dir!r}.", file=sys.stderr)
        sys.exit(1)

    normalized_data = normalize_to_baseline(data)

    if not any(normalized_data[g] for g in GROUP_ORDER):
        print(
            f"Error: no group had a usable {BASELINE_ALGO!r} value to normalize against.",
            file=sys.stderr,
        )
        sys.exit(1)

    palette = PALETTE
    if args.colors:
        palette = [c.strip() for c in args.colors.split(",")]
        if len(palette) != len(ALGO_ORDER):
            print(
                f"Error: --colors needs exactly {len(ALGO_ORDER)} colors "
                f"(one per algorithm {ALGO_ORDER}), got {len(palette)}.",
                file=sys.stderr,
            )
            sys.exit(1)
    algo_colors = dict(zip(ALGO_ORDER, palette))

    configure_font(args.font_family, font_path=args.font_path, font_bold_path=args.font_bold_path)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    plot_data(normalized_data, data, args.output, algo_colors)


if __name__ == "__main__":
    main()
