#!/usr/bin/env python3

# Run a simulation given a connection matrix file, and extract the last
# "finished at" time for flows involving nodes in a given array.
#
# Usage:
# python3 run_simulation.py <topology> <conn_matrix> <reps> <tracked_nodes> [other_params]
#
# Example:
# python3 run_simulation.py dfp connection_matrices/allgather.cm 3 "0,1,5,9" "-end 100000000 -q 364"

import subprocess
import re
import logging
import csv
from pathlib import Path
from random import choice
from argparse import ArgumentParser
from genera_collettive import genera_collettiva, genera_array

RED = "\033[91m"
RESET = "\033[0m"

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

TOPOLOGY_PARAM = {
    "dfp": {"nodes": 1332, "strat": "minimal"},
    "ft":  {"nodes": 1024, "strat": "ecmp_host"}
}

# Pattern: "Flow Roce_9_14 413 finished at 23.3024 total bytes 1 flow size 512"
FLOW_PATTERN = re.compile(
    r"Flow Uec_(\d+)_(\d+).*?finished at\s+([\d.]+)"
)

def parse_args():
    parser = ArgumentParser(description="Run a simulation on a given connection matrix.")
    parser.add_argument("topology",    type=str, help="Topology to simulate (e.g., 'dfp')")
    parser.add_argument("reps",        type=int, help="Number of repetitions")
    parser.add_argument("size",        type=int, help="Size")
    parser.add_argument("other",       type=str, nargs="?", default="", help="Additional simulation parameters")
    return parser.parse_args()

def extract_time(output_text):
    """Parses the LAST 'at <time>' value from the simulation output"""
    # list of all matches found in the text
    matches = re.findall(r"\bat\s+([\d.]+)", output_text)
    if matches:
        # Return the last match in the list, converted to float
        return float(matches[-1])
    return None


def extract_last_times(output: str, arrayA: list, arrayB: list):
    set_A = set(arrayA)
    set_B = set(arrayB)

    last_time_A = None
    last_time_B = None

    for line in output.splitlines():
        m = FLOW_PATTERN.search(line)
        if m:
            src, dst, t = int(m.group(1)), int(m.group(2)), float(m.group(3))

            if src in set_A and dst in set_A:
                last_time_A = t

            if src in set_B and dst in set_B:
                last_time_B = t

    return last_time_A, last_time_B


def ciao(topology, reps, size, other, perA, perB, type):

    if topology not in TOPOLOGY_PARAM:
        logging.error(f"Topology '{topology}' is not configured.")
        return

    parameter = TOPOLOGY_PARAM[topology]
    nodes = parameter['nodes']
    conns = parameter.get('conns', nodes)
    base_params = " ".join([f"-{k} {v}" for k, v in parameter.items()])


    times_only_A = []
    times_A_B = []

    arrayA, arrayB = genera_array("allgather_bine", "incast", perA, perB, type, nodes , conns, size, "ciao_A.cm", 0)
    _ = genera_collettiva("allgather_bine", "incast", perA, perB, type, nodes , conns, size, "ciao_A.cm", 0 , arrayA, arrayB, 0)
    conn_mat = "ciao_A.cm"
    cmd = f"./htsim_uec -tm {conn_mat} {base_params} {other}"

    #simulation of only A
    for i in range(1, reps + 1):
        logging.info(f"Running only A rep {i}/{reps}: {cmd}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            t = extract_time(result.stdout)
            times_only_A.append(t)

            # Print all simulation output
            #print(result.stdout)

        except subprocess.CalledProcessError as e:
            logging.error(f"Simulation failed: {e}")
        
    if times_only_A:
        avg_time_A = sum(times_only_A) / len(times_only_A)
        logging.info(f"{RED}Average for {size}: {avg_time_A:.4f}{RESET}")

    #simulation of A+B
    destination = []
    conn_mat = "ciao_A_B.cm"
    cmd = f"./htsim_uec -tm {conn_mat} {base_params} {other}"
    for i in range(1, reps + 1):
        logging.info(f"Running only A rep {i}/{reps}: {cmd}")
        d = choice(arrayB) 
        print(d)
        dest = genera_collettiva("allgather_bine", "incast", perA, perB, type, nodes , conns, size, "ciao_A_B.cm", 2 , arrayA, arrayB, d)

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            last_A, last_B = extract_last_times(result.stdout, arrayA, arrayB)
            logging.info(f"Last flow within arrayA finished at: {last_A}")
            logging.info(f"Last flow within arrayB finished at: {last_B}")
            times_A_B.append(last_A)
            destination.append(dest)
            if last_A > last_B:
                logging.error(f"{RED}Simulation failed: retry with {size} size ,{type}, percentuali: {perA},{perB} {RESET}")

        except subprocess.CalledProcessError as e:
            logging.error(f"Simulation failed: {e}")
    
    if times_A_B:
        avg_time_AB = sum(times_A_B) / len(times_A_B)
    
        worst_time_AB = max(times_A_B)
        worst_idx = times_A_B.index(worst_time_AB)
        w_node = destination[worst_idx]
        
        best_time_AB = min(times_A_B)
        best_idx = times_A_B.index(best_time_AB)
        b_node = destination[best_idx]

        logging.info(f"{RED}Average for {size}: {avg_time_AB:.4f}{RESET}")
        logging.info(
            f"{RED}Stats for {size} ->\n"
            f"  Avg:   {avg_time_AB:.4f}\n"
            f"  Worst: {worst_time_AB:.4f} (at index {worst_idx})\n"
            f"  Best:  {best_time_AB:.4f} (at index {best_idx}){RESET}"
        )
    
    return avg_time_A, avg_time_AB, worst_time_AB, w_node, best_time_AB, b_node

    


if __name__ == "__main__":

    #size = [1024, 16384, 131072, 1048576, 4194304, 16777216]
    size = [4194304, 16777216]
    types = ["blocco", "interleaved", "random"]

    csv_filename = "simulation_results.csv"
    headers = [
        "Type", "Size", "Perc", "Avg_A", "Avg_B", 
        "Worst_B", "Worst_B_Index", "Best_B", "Best_B_Index"
    ]

    # 2. Open the file in write mode ('w') and initialize the CSV writer
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()  # Writes the top row with names
        
        print("DOING TEST 20/80")

        # 3. Run your nested simulation loops
        for t in types:
            for s in size:
                # Note: Fixed the duplicate 'iB' variable names from your original snippet 
                # to separate variables: worst_idx_B and best_idx_B
                avgA, avgB, wB, worst_idx_B, bB, best_idx_B = ciao(
                    "ft", 3, s, 
                    "-end 100000000 -q 364 -linkspeed 400000 -hop_latency 0.02 -switch_latency 0.25 -load_balancing_algo reps", 
                    0.20, 0.80, t
                )
                
                # 4. Map the loop inputs and simulation outputs into a dictionary row
                row_data = {
                    "Type": t,
                    "Size": s,
                    "Perc": "20/80",
                    "Avg_A": f"{avgA:.4f}" if isinstance(avgA, (int, float)) else avgA,
                    "Avg_B": f"{avgB:.4f}" if isinstance(avgB, (int, float)) else avgB,
                    "Worst_B": f"{wB:.4f}" if isinstance(wB, (int, float)) else wB,
                    "Worst_B_Index": worst_idx_B,
                    "Best_B": f"{bB:.4f}" if isinstance(bB, (int, float)) else bB,
                    "Best_B_Index": best_idx_B
                }
                
                # 5. Write the row straight to the CSV
                writer.writerow(row_data)

        print("DOING TEST 50/50")

        for t in types:
            for s in size:
                # Note: Fixed the duplicate 'iB' variable names from your original snippet 
                # to separate variables: worst_idx_B and best_idx_B
                avgA, avgB, wB, worst_idx_B, bB, best_idx_B = ciao(
                    "ft", 3, s, 
                    "-end 100000000 -q 364 -linkspeed 400000 -hop_latency 0.02 -switch_latency 0.25 -load_balancing_algo reps", 
                    0.50, 0.50, t
                )
                
                # 4. Map the loop inputs and simulation outputs into a dictionary row
                row_data = {
                    "Type": t,
                    "Size": s,
                    "Perc": "50/50",
                    "Avg_A": f"{avgA:.4f}" if isinstance(avgA, (int, float)) else avgA,
                    "Avg_B": f"{avgB:.4f}" if isinstance(avgB, (int, float)) else avgB,
                    "Worst_B": f"{wB:.4f}" if isinstance(wB, (int, float)) else wB,
                    "Worst_B_Index": worst_idx_B,
                    "Best_B": f"{bB:.4f}" if isinstance(bB, (int, float)) else bB,
                    "Best_B_Index": best_idx_B
                }
                
                # 5. Write the row straight to the CSV
                writer.writerow(row_data)
        
        print("DOING TEST 10/90")
        for t in types:
            for s in size:
                # Note: Fixed the duplicate 'iB' variable names from your original snippet 
                # to separate variables: worst_idx_B and best_idx_B
                avgA, avgB, wB, worst_idx_B, bB, best_idx_B = ciao(
                    "ft", 3, s, 
                    "-end 100000000 -q 364 -linkspeed 400000 -hop_latency 0.02 -switch_latency 0.25 -load_balancing_algo reps", 
                    0.10, 0.90, t
                )
                
                # 4. Map the loop inputs and simulation outputs into a dictionary row
                row_data = {
                    "Type": t,
                    "Size": s,
                    "Perc": "10/90",
                    "Avg_A": f"{avgA:.4f}" if isinstance(avgA, (int, float)) else avgA,
                    "Avg_B": f"{avgB:.4f}" if isinstance(avgB, (int, float)) else avgB,
                    "Worst_B": f"{wB:.4f}" if isinstance(wB, (int, float)) else wB,
                    "Worst_B_Index": worst_idx_B,
                    "Best_B": f"{bB:.4f}" if isinstance(bB, (int, float)) else bB,
                    "Best_B_Index": best_idx_B
                }
                
                # 5. Write the row straight to the CSV
                writer.writerow(row_data)

    print(f"All simulation results saved successfully to {csv_filename}!")

    