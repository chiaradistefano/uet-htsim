# Generate a bruck all-to-all traffic matrix.
# python gen_alltoall_bruck.py <filename> <nodes> <conns> <flowsize>
# Parameters:
# <nodes>   number of nodes in the topology
# <conns>    number of active connections
# <flowsize>   size of the flows in bytes

import sys
import math


def create_connection(conns, flowsize, array_nodes, id, trig_id):

    lines = []
    power_2=False
    if conns > 0 and (conns & (conns - 1)) == 0:
        power_2=True
        max_step=int(math.log2(conns))
    else:
        max_step=int(math.log2(conns))+1

    for n in range(0,conns):
        src=n
        for step in range(max_step):
            id+=1

            if step!=0:
                src=dst

            dst=(src+(2**step))%conns

            out = str(array_nodes[src]) + "->" + str(array_nodes[dst]) + " id " + str(id)

            if step == 0:
                out = out + " start 0"
            else:
                out = out + " trigger " + str(trig_id)
                trig_id += 1

            n_flows = 0
            for i in range(conns):
                if (i & (1 << step)) != 0:
                    n_flows+=1
            
            out = out + " size " + str(int((flowsize/conns)*n_flows))


            if step != max_step-1:
                out = out + " send_done_trigger " + str(trig_id)
            lines.append(out)

    return lines, id, trig_id

def main():
    if len(sys.argv) != 5:
        print("Usage: python gen_alltoall_bruck.py <filename> <nodes> <conns> <flowsize>")
        sys.exit()
    filename = sys.argv[1]
    nodes = int(sys.argv[2])
    conns = int(sys.argv[3])
    flowsize = int(sys.argv[4])

    array_nodes = list(range(conns))
    id = 0
    trig_id = 1


    print("Connections: ", conns)
    print("Flowsize: ", flowsize, "bytes")

    lines, _, final_trig_id = create_connection(conns, flowsize, array_nodes, id, trig_id)

    num_flows = len(lines)


    for t in range(trig_id, final_trig_id):
        out = "trigger id " + str(t) + " oneshot"
        lines.append(out)

    with open(filename, "w") as f:
        print(f"Nodes", nodes, file=f)
        print(f"Connections", num_flows, file=f) 
        print(f"Triggers", final_trig_id - 1, file=f)  
        
        for line in lines:
            print(line, file=f)

if __name__ == "__main__":
    main()

