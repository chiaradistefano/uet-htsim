# Python script to generate connection matrices

import subprocess
import sys
import os
import ast
import utils

# python gen_conn_matrices.py <coll> <nodes> <conns> <flowsize>
# Parameters:
# <coll>    string containing the list of collective operations to generate connection matrices 
#           (e.g. "allgather_bine|allreduce|permutation") or give already the set of collective {'allgather_bruck'}
#           if no specific algorithm is provided, all implemented algorithms for that collective will be processed
# <nodes>   number of nodes in the topology
# <conns>   number of active connections
# <flowsize>    size of the flows in bytes (e.g. "2KB|1MB|16KB|512B")

def main():
    if len(sys.argv) != 5:
        print("Usage: python gen_conn_matrices.py <coll> <nodes> <conns> <flowsize>")
        sys.exit()
    operations = sys.argv[1]
    nodes = sys.argv[2]
    conns = sys.argv[3]
    flowsizes = sys.argv[4]

    sizes = utils.to_bytes(flowsizes.split('|'))
    new, old, fail = set(), set(), set()

    if operations.startswith('{'):
        set_ops = ast.literal_eval(operations)
    else:
        set_ops = utils.get_operations(operations.split('|'))
            
    print(f"Collective: {set_ops} | Nodes: {nodes} | Conns: {conns} | Flowsize: {sizes}")

    for op in set_ops:
        for size in sizes:
            if size >= 1073741824:
                new_file = f"{op}_{nodes}n_{conns}c_{size // 1073741824}GiB.cm"
            elif size >= 1048576:
                new_file = f"{op}_{nodes}n_{conns}c_{size // 1048576}MiB.cm"
            elif size >= 1024:
                new_file = f"{op}_{nodes}n_{conns}c_{size // 1024}KiB.cm"
            else:
                new_file = f"{op}_{nodes}n_{conns}c_{size}B.cm"
            operation = os.path.join("connection_matrices", f"gen_{op}.py")
            folder = os.path.join("connection_matrices", f"{op}")

            # check if the file already exist
            file_path = os.path.join(folder, new_file)

            if not os.path.exists(folder):
                os.makedirs(folder)
            else:
                if os.path.isfile(file_path):
                    print(f"File {new_file} already exist")
                    old.add(new_file)
                    continue
            
            # command: python connection_matrices/gen_operation.py <filename> <nodes> <conns> <flowsize>
            command = ["python3", operation, file_path, nodes, conns, str(size)]

            try:
                subprocess.run(command, check=True)
                new.add(new_file)
                print(f"Successfully generated: {new_file}")
            except subprocess.CalledProcessError as e:
                print(f"Error: Command failed for {op} with error: {e}")
                fail.add(new_file)
                continue
            except FileNotFoundError:
                print(f"Error: 'gen_{op}.py' was not found in this directory")
                fail.add(new_file)
                continue

    print("-" * 100)
    if new:
        print(f"Successfully generated: {new}")
    if old:
        print(f"Unchanged files: {old}")
    if fail:
        print(f"Failed files: {fail}")

if __name__ == "__main__":
    main()
