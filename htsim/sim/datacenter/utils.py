# Shared utilities for simulation scripts.

from pathlib import Path
import csv
import re

# Set-based registry
COLLECTIVES_MAP = {
    "allgather":     {"allgather_bine", "allgather_bruck", "allgather_recdub",
                      "allgather_ring", "allgather_sparbit"},
    "allreduce":     {"allreduce_bine", "allreduce_recdub"},
    "reducescatter": {"reducescatter_bine", "reducescatter_recdub",
                      "reducescatter_rechalv", "reducescatter_pairwise"},
    "alltoall":      {"alltoall_bruck", "alltoall_pairwise"},
}

def to_bytes(flowsize: list[str]) -> list[int]:
    """Convert a list of human-readable size strings to byte counts.
 
    Parameters
    ----------
    flowsize: List of size strings, e.g. ``["1MiB", "512KiB", "2GiB"]``.
 
    Returns
    -------
    List of byte values corresponding to each valid input entry.
 
    Examples
    --------
    >>> to_bytes(["1KiB", "2MiB"])
    [1024, 2097152]
    """

    sizes = []
    for size in flowsize:
        size = size.strip()
        if "KiB" in size:
            sizes.append(int(size.replace("KiB", ""))*1024)
        elif "MiB" in size:
            sizes.append(int(size.replace("MiB", ""))*1048576)
        elif "GiB" in size:
            sizes.append(int(size.replace("GiB", ""))*1073741824)
        elif "B" in size or size.isdigit():
            sizes.append(int(size.replace("B", "")))
        else: 
            print(f"This size {size} is not supported, skipping")
    return sizes

def normalize_sizes(flowsize_str: str) -> list[str]:
    """Parses and normalizes a ``|``-separated string flow sizes
    
    Parameters
    ----------
    flowsize_str: Pipe-separated size string, e.g. ``"1MiB|512KiB|256"``.
 
    Returns
    -------
    List of normalised size strings, e.g. ``["1MiB", "512KiB", "256B"]``.
    """
    sizes = []
    units = ("KiB", "MiB", "GiB", "B")
    
    for s in flowsize_str.split('|'):
        size = s.strip()
        if any(u in size for u in units):
            sizes.append(size)
        elif size.isdigit():
            sizes.append(f"{size}B")
        else:
            print(f"Unsupported size format: '{s}', skipping") 
    return sizes

def get_operations(ops: list[str]) -> set[str]:
    """Resolve a list of operation specifiers to a set of algorithm for names.
 
    Each entry in *ops* can be either:
 
    - A **collective name** (e.g. ``"allgather"``): all known algorithms for
      that collective are added.
    - A **specific algorithm** (e.g. ``"allgather_ring"``): added only if it
      exists in the registry.
 
    Parameters
    ----------
    ops: Mixed list of collective names and/or specific algorithm identifiers.
 
    Returns
    -------
    Fully resolved set of algorithm name strings.
    """
    operation = set()
    for op in ops:
        if '_' in op:
            # check if the collective operation and algorithm exist or not
            collective = op.split('_')[0]
            if op in COLLECTIVES_MAP.get(collective, set()):
                operation.add(op)
            else:
                print(f"Collective operation '{op}' not found or has no algorithms, skipping") 
        else:
            # default collectives: if no specific algorithm is provided
            algorithms = COLLECTIVES_MAP.get(op, set()) 
            if not algorithms:
                print(f"Collective operation '{op}' not found or has no algorithms, skipping") 
            operation |= algorithms
    return operation

def create_csv(filename: str) -> None:
    """Create a simulation-results CSV file with headers if it does not exist.

    Parameters
    ----------
    filename: Path to the target CSV file.
    """
    path = Path(filename)
    if not path.exists():
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['nodes', 'conns', 'operation', 'size', 'time', 'strat'])

def result_exists(filename: str, nodes: int, conns: int, operation: str, size: str, strat: str) -> bool:
    """Checks if a specific simulation result is already recorded.

    Parameters
    ----------
    filename:  Path to the results CSV.
    nodes:     Node count.
    conns:     Connection count.
    operation: Algorithm name.
    size:      Message size.
    strat:     Routing algorithm.
    """
    path = Path(filename)
    if not path.exists():
        return False
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row['nodes'] == str(nodes) and 
                row['conns'] == str(conns) and 
                row['operation'] == operation and 
                row['size'] == size and row['strat'] == strat):
                return True
    return False

def extract_time(output_text: str) -> float | None:
    """Parses the LAST 'at <time>' value from the simulation output"""
    # list of all matches found in the text
    matches = re.findall(r"\bat\s+([\d.]+)", output_text)
    if matches:
        # Return the last match in the list, converted to float
        return float(matches[-1])
    return None

def get_ports_from_idmap(filename) -> list[str]:
    """Extracts unique clean port names 'SRC8->LF1' from idmap.txt.
    
    Parameters
    ----------
    filename: Path to the ``idmap.txt`` file generated by the simulator.
 
    Returns
    -------
    List of port-name strings.  Returns an empty list if the
    file does not exist.
    """
    path = Path(filename)
    if not path.exists():
        print(f"Error: File not found at {filename}")
        return []

    port_pattern = re.compile(r'^(?!Pipe-)(\w+->\w+(?:\(\d+\))?)$')
    ports = []

    with path.open('r') as f:
        for line in f:
            # Strip whitespace and the leading ID number/space (e.g., "52 ")
            clean_line = re.sub(r'^\d+\s+', '', line.strip())
            
            match = port_pattern.search(clean_line)
            if match:
                ports.append(match.group(1))

    return ports

def get_average_utilization(file_path: str, simulation_time: float, output_file: str) -> None:
    '''Compute per-port average utilization and write results to a CSV

    Parameters
    ----------
    file_path:       Path to the raw log packet CSV from the
                     simulator.
    simulation_time: Total simulation duration in **microseconds**.
    output_file:     Path for the output CSV.  Overwritten if it already
                     exists. 
 
    Output CSV columns
    ------------------
    ``Port Name``, ``Total Utilization`` (us), ``Average Utilization`` (ratio)
    '''
    avg_utilization = {}

    ports = get_ports_from_idmap("idmap.txt")

    for p in ports:
        avg_utilization[p] = 0

    try:
        with open(file_path, mode='r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not row or len(row) < 4: continue
                
                port_name = row[0].strip()

                # Convert duration (picoseconds to microseconds)
                duration = float(row[3].strip()) / 1000000 
                
                if port_name in avg_utilization:
                    avg_utilization[port_name] += duration
                else:
                    print("Error", port_name)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    with open(output_file, mode='w', newline='') as f:
        f.write(f"# Total Simulation Time: {simulation_time} \n")
                
        writer = csv.writer(f)
        writer.writerow(["Port Name", "Total Utilization", "Average Utilization"])

        for port, total_dur in avg_utilization.items():
            if total_dur == 0:
                avg = 0
            else:
                avg = total_dur / simulation_time
            writer.writerow([port, f"{total_dur:.5f}", f"{avg:.5f}"])

def filter_port_type_dfp(df, port_type):
    """Filter a DataFrame to rows matching a Dragonfly+ port category.
 
    Port categories and their matched port-name patterns:
 
    - ``spine-spine`` : Spine-to-spine links (SP<n>->SP<m>).
    - ``leaf-spine``  : Bidirectional leaf-spine links.
    - ``no-host``     : All links that are NOT host-facing (excludes DST/SRC).
    - ``host-leaf``   : Host-facing links only (port names containing DST or SRC).
    - ``all``         : No filtering; the full DataFrame is returned unchanged.
 
    Parameters
    ----------
    df:        DataFrame.
    port_type: One of the category strings listed above.
 
    Returns
    -------
    Filtered copy of *df*.
    """
    patterns = {
        "spine-spine": r'^SP\d+->SP\d+(?:\(\d+\))?$',
        "leaf-spine": r'^(?:SP\d+->LF\d+|LF\d+->SP\d+)(?:\(\d+\))?$',
        "no-host": r'^(?!.*(?:DST|SRC)).*$',
        "host-leaf" : r'DST|SRC'
    }
    
    if port_type in patterns:
        return df[df['Port Name'].str.contains(patterns[port_type], na=False, regex=True)].copy()
    return df

def filter_port_type_ft(df, port_type):
    """Filter a DataFrame to rows matching a Fat-Tree port category.
 
    Port categories and their matched port-name patterns:
 
    - ``upper-core``  : Upper-switch to core-switch links (US<n>->CS<m>).
    - ``lower-upper`` : Lower-switch to upper-switch links (LS<n>->US<m>).
    - ``no-host``     : All links that are NOT host-facing (excludes DST/SRC).
    - ``lower-host``  : Host-facing links only (port names containing DST or SRC).
    - ``all``         : No filtering; the full DataFrame is returned unchanged.
 
    Parameters
    ----------
    df:        DataFrame.
    port_type: One of the category strings listed above.
 
    Returns
    -------
    Filtered copy of *df*.
    """
    patterns = {
        "upper-core": r'^(?:US\d+->CS\d+|CS\d+->US\d+)(?:\(\d+\))?$', 
        "lower-upper": r'^(?:LS\d+->US\d+|US\d+->LS\d+)(?:\(\d+\))?$', 
        "no-host": r'^(?!.*(?:DST|SRC)).*$',
        "lower-host" : r'DST|SRC'
    }
    
    if port_type in patterns:
        return df[df['Port Name'].str.contains(patterns[port_type], na=False, regex=True)].copy()
    return df

def name_collective(collective):
    """Name of the collective for the plot"""
    if '_' in collective:
        # check if the collective operation and algorithm exist or not
        tmp = collective.split('_')
        return tmp[1] 
    else:
        if collective == 'allgather': 
            return "AllGather"
        elif collective == 'allreduce': 
            return "AllReduce"
        elif collective == 'reducescatter': 
            return "Reduce-Scatter"
        elif collective == 'alltoall':
            return "AllToAll"
        else:
            print(f"Collective operation {collective} not implemented")
