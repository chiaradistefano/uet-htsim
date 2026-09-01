# Python script to run simulations

import subprocess
import csv
import logging
from pathlib import Path
from argparse import ArgumentParser
import utils

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Parameters for specific topologies (if the number of connections is not specified, conns = nodes)
TOPOLOGY_PARAM = {
    "dfp": {"nodes": 1332, "conns": 1024, "strat": "minimal"},
    "ft":  {"nodes": 1024, "strat": "ecmp_host"}
}

def parse_args():
    parser = ArgumentParser(description="Run network simulations for various topologies and collectives.")
    parser.add_argument("coll", type=str, help="Collective operations (e.g., 'allreduce|allgather_bine')")
    parser.add_argument("topology", type=str, help="Topologies to simulate (e.g., 'ft|dfp')")
    parser.add_argument("flowsize", type=str, help="Flow sizes (e.g., '2KB|1MB|512B')")
    parser.add_argument("reps", type=int, help="Number of repetitions per simulation")
    parser.add_argument("other", type=str, nargs="?", default="", help="Additional simulation parameters")
    parser.add_argument("--log", action="store_true", default=False,
                        help="Enable packet logging on the final repetition of each simulation run")
    parser.add_argument("--force", action="store_true", default=False,
                        help="Re-run simulations even if results already exist in the output CSV")
    return parser.parse_args()

def main():
    args = parse_args()

    set_ops = utils.get_operations(args.coll.split('|'))
    mess_sizes = utils.normalize_sizes(args.flowsize)
    topologies = args.topology.split('|')
    log = args.log
    force = args.force

    for topo in topologies:
        if topo not in TOPOLOGY_PARAM:
            logging.error(f"Topology '{topo}' has no configuration or isn't implemented.")
            continue

        res_file = f"{topo}_result.csv"
        utils.create_csv(res_file) 

        parameter = TOPOLOGY_PARAM[topo]
        nodes = parameter['nodes']
        conns = parameter.get('conns', nodes)
        strat = parameter['strat']

        # Build base params for the executable safely
        base_params = " ".join([f"-{k} {v}" for k, v in parameter.items() if k != "conns"])

        # Generate Connection Matrices
        logging.info(f"Generating matrices for topology '{topo}'...")
        # FIX: Instead of passing str(set_ops) which passes literal Python list formatting like "['allgather']",
        # join the elements cleanly or pass the original raw string argument depending on what gen_conn_matrices.py needs.
        coll_arg = "|".join(set_ops) 
        gen_cmd = ["python3", "gen_conn_matrices.py", coll_arg, str(nodes), str(conns), args.flowsize]
        
        try:
            subprocess.run(gen_cmd, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to generate connection matrices for topology '{topo}'. Error: {e}")
            continue 

        # Run Simulations
        for coll in set_ops:
            for size in mess_sizes:
                if not force and utils.result_exists(res_file, nodes, conns, coll, size, strat):
                    logging.info(f"Skip: {topo}/{coll}/{size} already exists in {res_file}")
                    continue

                times = []
                conn_mat = Path(f"connection_matrices/{coll}/{coll}_{nodes}n_{conns}c_{size}.cm")
                
                # Check beforehand if matrix file actually exists to avoid execution crashes
                if not conn_mat.exists():
                    logging.error(f"Matrix file missing: {conn_mat}. Skipping combination.")
                    continue

                base_cmd = f"./htsim_roce_{topo} -tm {conn_mat} {base_params} {args.other}"

                for i in range(1, args.reps + 1):
                    cmd = base_cmd  
                    if i == args.reps and log:
                        cmd += " -log packet"
                        logging.info(f"Running: {topo} | {coll} | {size} | Rep {i}/{args.reps} (with packet logging)")
                    else:
                        logging.info(f"Running: {topo} | {coll} | {size} | Rep {i}/{args.reps}")

                    try:
                        # execution with shell=True is retained to handle space-delimited string args cleanly
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
                        t = utils.extract_time(result.stdout)

                        if t is not None:
                            times.append(t)
                            if i == args.reps and log:  
                                log_dir = Path(f"log/{topo}")
                                log_dir.mkdir(parents=True, exist_ok=True)
                                output_filename = log_dir / f"{coll}_{nodes}n_{conns}c_{size}.csv"
                                utils.get_average_utilization("packets.csv", t, str(output_filename))
                        else:
                            logging.error(f"Could not parse timestamp from output. Raw output was: {result.stdout.strip()}")

                    except subprocess.CalledProcessError as e:
                        # FIX: Print stdout and stderr on crash to allow tracking simulator problems
                        logging.error(f"Simulation execution failed for command: {cmd}")
                        if e.stdout:
                            logging.error(f"Simulator stdout: {e.stdout.strip()}")
                        if e.stderr:
                            logging.error(f"Simulator stderr: {e.stderr.strip()}")

                # Calculate Average and Save
                if times:
                    avg_time = sum(times) / len(times)
                    with open(res_file, 'a', newline='') as f:
                        csv.writer(f).writerow([nodes, conns, coll, size, round(avg_time, 4), strat])
                    logging.info(f"Average for {coll}/{size}: {avg_time:.4f}")
                else:
                    logging.warning(f"No successful execution cycles captured for {topo}/{coll}/{size}. Progress not saved.")

if __name__ == "__main__":
    main()