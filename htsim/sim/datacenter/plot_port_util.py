"""
Generates port-utilization distribution plots for collective-communication
algorithms simulated over different network topologies (Dragonfly+ and Fat-Tree).

Each plot compares the average utilization distribution of every algorithm
that implements a given collective operation (allgather, allreduce, alltoall,
reducescatter) on a chosen port category.

Supported plot types
--------------------
- hist     : stepped histogram with a log-scale y-axis.
- kde      : kernel-density estimate with filled curves.
- boxplot  : horizontal box-and-strip plot.
- multi    : per-algorithm faceted histogram grid.

Output
------
Plots are saved under:
    log/<topology>/plot/<collective>/<plot_type>/<collective>_<port_type>_<plot_type>.png
"""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import pandas as pd
import seaborn as sns
import utils

# Print target: 400 x 250 mm => 15.75 x 9.84 in, with true printed-point font sizes.
FIGSIZE = (15.75, 9.84)
PRINT_RCPARAMS = {
    "font.size": 28,
    "axes.labelsize": 30,
    "xtick.labelsize": 26,
    "ytick.labelsize": 28,
    "legend.fontsize": 26,
    "axes.linewidth": 1.5,
}


def read_sim_time(filename) -> float:
    """Read the '# Total Simulation Time:' value from a results CSV.

    The value lives in a leading comment line that ``pd.read_csv(comment="#")``
    skips, so it is read directly off the raw file.
    """
    with open(filename) as fh:
        m = re.search(r"Total Simulation Time:\s*([\d.]+)", fh.readline())
    return float(m.group(1)) if m else float("nan")


# List-based registry
COLLECTIVE_MAP = {
    'allgather': ['allgather_bine', 'allgather_sparbit', 'allgather_bruck', 'allgather_recdub', 'allgather_ring'],
    'allreduce': ['allreduce_bine', 'allreduce_recdub'],
    'reducescatter': ['reducescatter_bine', 'reducescatter_recdub', 'reducescatter_rechalv', 'reducescatter_pairwise'],
    'alltoall': ['alltoall_bruck', 'alltoall_pairwise']
}

def get_data_for_plot(topology: str, collective: str, nodes: str, conns: str,
                       size: str, port_type: str) -> pd.DataFrame | None:
    """Load and merge per-algorithm CSV logs for a given collective operation,
    filters rows by *port_type* and discards ports with zero average utilization.

    Parameters
    ----------
    topology:   Network topology identifier, e.g. "dfp" or "ft"
    collective: Collective operation name
    nodes:      Number of nodes
    conns:      Number of connections
    size:       Message size 
    port_type:  Port-category filter

    Returns
    -------
    pd.DataFrame
        A concatenated DataFrame with all algorithms
    None
        Returned when *collective* is unknown or any expected CSV file is
        missing.
    """

    algorithms = COLLECTIVE_MAP.get(collective)
    if algorithms is None:
        print(f"Collective operation '{collective}' not found or has no algorithms")
        return None

    if port_type == "local-global":
        sub_types_dfp = [("leaf-spine", "Local (leaf-spine)"),
                     ("spine-spine", "Global (spine-spine)")]
        sub_types_ft = None
    elif port_type == "host-nohost":
        sub_types_ft = [("lower-host", "Local (host-lower)"),
                     ("no-host", "Others")]
        sub_types_dfp = None
    else:
        sub_types_dfp = None
        sub_types_ft = None

    all_dfs = []

    for algo in algorithms:
        filename = Path(f"log/{topology}/{algo}_{nodes}n_{conns}c_{size}.csv")
        if not filename.exists():
            print(f"Missing file: {filename}")
            return None

        df = pd.read_csv(filename, comment="#")
        clean = str(utils.name_collective(algo)).capitalize()
        sim_time = read_sim_time(filename)

        if sub_types_dfp is not None:
            sub_frames = []
            counts = {}  
            for sub_pt, link_label in sub_types_dfp:
                sub = utils.filter_port_type_dfp(df, sub_pt)
                total_ports = len(sub)
                sub = sub[sub["Average Utilization"] != 0].copy()
                active_ports = len(sub)

                counts[link_label] = f"{(active_ports / total_ports) * 100:.2f}%"
                sub["Clean Algo"] = clean
                sub["Link Type"] = link_label
                sub_frames.append(sub)

            # Y-axis label: sim time and per-link used/total ports (no algo name).
            algo_label = (
                f"t: {sim_time:.2f} \u00b5s\n"
                f"Local: {counts['Local (leaf-spine)']}\n"
                f"Global: {counts['Global (spine-spine)']}"
            )
            for sub in sub_frames:
                sub["Algo Label"] = algo_label
                all_dfs.append(sub)
            continue
        
        if sub_types_ft is not None:
            sub_frames = []
            counts = {}  
            for sub_pt, link_label in sub_types_ft:
                sub = utils.filter_port_type_ft(df, sub_pt)
                total_ports = len(sub)
                sub = sub[sub["Average Utilization"] != 0].copy()
                active_ports = len(sub)

                counts[link_label] = f"{active_ports}/{total_ports}"
                sub["Clean Algo"] = clean
                sub["Link Type"] = link_label
                sub_frames.append(sub)

            # Y-axis label: sim time and per-link used/total ports (no algo name).
            algo_label = (
                f"t: {sim_time:.2f} \u00b5s\n"
                f"%Local: {counts['Local (host-lower)']}\n"
                f"%Others: {counts['Others']}"
            )
            for sub in sub_frames:
                sub["Algo Label"] = algo_label
                all_dfs.append(sub)
            continue

        # Apply topology-specific port-type filter
        if topology == "dfp":
            df = utils.filter_port_type_dfp(df, port_type)
        else:
            df = utils.filter_port_type_ft(df, port_type)

        total_ports = len(df)

        # Keep only ports that were actually active during the simulation
        df = df[df["Average Utilization"] != 0].copy()
        active_ports = len(df)

        # Facet-title label (multi) and legend/y-tick label carry the sim time.
        df["Clean Algo"] = f"{clean}\n{sim_time:.2f} \u00b5s"
        df["Algorithm (Used/ Total Ports)"] = (
            f"{clean} ({active_ports}/{total_ports})\n{sim_time:.2f} \u00b5s"
        )
        all_dfs.append(df)

    return pd.concat(all_dfs, ignore_index=True)


def create_plot_comparison(topology: str, collective: str, nodes: str, conns: str, 
                           size: str, port_type: str, plot_type: str) -> bool:
    """Generate and save a utilization-distribution comparison plot.

    Parameters
    ----------
    topology:   Network topology identifier, e.g. "dfp" or "ft"
    collective: Collective operation name
    nodes:      Number of nodes
    conns:      Number of connections
    size:       Message size 
    port_type:  Port-category filter forwarded to the topology-specific
    plot_type:  Plot type

    Returns
    -------
    bool
        ``True`` on success, ``False`` if data could not be loaded.
    """
    # The combined local/global overlay is only defined for the boxplot.
    if port_type == "local-global" and plot_type != "boxplot":
        return False
    
    if port_type == "host-nohost" and plot_type != "boxplot":
        return False

    df = get_data_for_plot(topology, collective, nodes, conns, size, port_type)
    if df is None:
        return False

    sns.set_theme(style="ticks")
    plt.rcParams.update(PRINT_RCPARAMS)
    plt.rcParams["figure.titlesize"] = plt.rcParams["axes.titlesize"]

    hue_col = "Algorithm (Used/ Total Ports)"
    x_col = "Average Utilization"
    title = (
        f"{utils.name_collective(collective)} "
        f"{plot_type.capitalize()} Port Utilization ({port_type})"
    )

    if plot_type == "hist":
        g = sns.displot(
            data=df, x=x_col, hue=hue_col,
            kind="hist", stat="count", element="step", alpha=0.3,
            height=5, aspect=3,
        )
        g.figure.set_size_inches(*FIGSIZE)
        g.ax.set_yscale("log")
        g.ax.set_ylim(1, None)
        g.figure.suptitle(title, y=1.02)

    elif plot_type == "kde":
        g = sns.displot(
            data=df, x=x_col, hue=hue_col,
            kind="kde", common_norm=False,
            height=5, aspect=3, fill=True,
            warn_singular=False,
        )
        g.figure.set_size_inches(*FIGSIZE)
        g.figure.suptitle(title, y=1.02)

    elif plot_type == "boxplot":
        fig, ax = plt.subplots(figsize=FIGSIZE)

        if port_type == "local-global":
            # Two boxes per algorithm: local (leaf-spine) vs global (spine-spine).
            y_col = "Algo Label"
            link_col = "Link Type"
            hue_order = ["Local (leaf-spine)", "Global (spine-spine)"]
            order = df[y_col].drop_duplicates().tolist()
            palette = {
                "Local (leaf-spine)": "#2e7d7d",
                "Global (spine-spine)": "#C0492E",
            }
            sns.boxplot(
                data=df, x=x_col, y=y_col, hue=link_col,
                order=order, hue_order=hue_order,
                whis=[0, 100], width=0.7, gap=0.25, palette=palette,
                ax=ax,
            )
            sns.stripplot(
                data=df, x=x_col, y=y_col, hue=link_col,
                order=order, hue_order=hue_order,
                size=3, palette=[".25", ".25"], alpha=0.45, dodge=True,
                legend=False, ax=ax,
            )
            ax.legend(title="Link type", loc="lower right")
            ax.tick_params(axis="y", labelsize=plt.rcParams["ytick.labelsize"] * 0.8)
        elif port_type == "host-nohost":
            # Two boxes per algorithm: host (host-lower) vs others.
            y_col = "Algo Label"
            link_col = "Link Type"
            hue_order = ["Local (host-lower)", "Others"]
            order = df[y_col].drop_duplicates().tolist()
            palette = {
                "Local (host-lower)": "#8198b8",   
                "Others": "#bc817f", 
            }
            sns.boxplot(
                data=df, x=x_col, y=y_col, hue=link_col,
                order=order, hue_order=hue_order,
                whis=[0, 100], width=0.7, gap=0.25, palette=palette,
                ax=ax,
            )
            sns.stripplot(
                data=df, x=x_col, y=y_col, hue=link_col,
                order=order, hue_order=hue_order,
                size=3, palette=[".25", ".25"], alpha=0.45, dodge=True,
                legend=False, ax=ax,
            )
            ax.legend(title="Link type", loc="lower right")
            ax.tick_params(axis="y", labelsize=plt.rcParams["ytick.labelsize"] * 0.8)
        else:
            sns.boxplot(
                data=df, x=x_col, y=hue_col, hue=hue_col,
                whis=[0, 100], width=0.6, palette="vlag", legend=False,
                ax=ax,
            )
            sns.stripplot(
                data=df, x=x_col, y=hue_col,
                size=4, color=".3", alpha=0.5,
                ax=ax,
                
            )

        ax.xaxis.grid(True)
        ax.set(ylabel="")
        if port_type not in ("local-global", "host-nohost"):
            ax.set_title(title)
        sns.despine(trim=True, left=True)

        if port_type in ("local-global", "host-nohost"):
            # Put each algorithm name, rotated vertically, just to the left of
            # its Time/port label block. Draw once first so the tick-label
            # extents are known, then anchor the name past the widest label.
            name_by_label = (
                df.drop_duplicates("Algo Label")
                  .set_index("Algo Label")["Clean Algo"].to_dict()
            )
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            inv = ax.transAxes.inverted()
            left = min(
                inv.transform((lbl.get_window_extent(renderer).x0, 0))[0]
                for lbl in ax.get_yticklabels()
            )
            trans = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
            for tick, lbl in zip(ax.get_yticks(), ax.get_yticklabels()):
                ax.text(
                    left - 0.03, tick, name_by_label.get(lbl.get_text(), ""),
                    transform=trans, rotation=90, va="center", ha="center",
                )

    elif plot_type == "multi":
        g = sns.displot(
            data=df, x=x_col, hue=hue_col, row="Clean Algo",
            kind="hist", stat="count", element="step", alpha=0.3,
            height=3, aspect=3,
        )
        g.figure.set_size_inches(FIGSIZE[0], FIGSIZE[1] * max(1, df["Clean Algo"].nunique() / 3))
        g.set_titles(row_template="{row_name}")
        for ax in g.axes.flat:
            if ax is not None:
                ax.set_yscale("log")
                ax.set_ylim(1, None)
        g.figure.suptitle(title, y=1.02)

    else:
        print(f"Unknown plot type '{plot_type}'. Choose from: hist, kde, boxplot, multi.")
        return False

    output_dir = Path(f"log/{topology}/plot/{collective}/{plot_type}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{collective}_{port_type}_{plot_type}.pdf"

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    return True

def main():
    """Run the full batch of comparison plots for both topologies.

    Dragonfly+ port categories  : spine-spine, leaf-spine, no-host, host-leaf, all
    Fat-Tree port categories : upper-core, lower-upper, no-host, lower-host, all
    """
    plot_types = ["boxplot", "hist", "kde", "multi"]
    collectives = ["allgather"]
    port_categories_dfp = ["spine-spine", "leaf-spine", "no-host", "host-leaf", "all", "local-global"]
    port_categories_ft  = ["upper-core", "lower-upper", "no-host", "lower-host", "all", "host-nohost"]

    for plot_type in plot_types:
        for collective in collectives:
            for port in port_categories_dfp:
                create_plot_comparison("dfp", collective, "1332", "1024", "1MiB", port, plot_type)
            #for port in port_categories_ft:
                #create_plot_comparison("ft",  collective, "1024", "1024", "1MiB", port, plot_type)


if __name__ == "__main__":
    main()