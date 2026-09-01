# Generate a isend-irecv all-to-all traffic matrix.
# python gen_alltoall_isend.py <filename> <nodes> <conns> <flowsize> 
# Parameters:
# <nodes>   number of nodes in the topology
# <conns>    number of active connections
# <flowsize>   size of the flows in bytes

import sys
import math

def create_connection(conns, flowsize, array_nodes, id, trig_id, start_after, last):
    lines = []

    for n in range(0,conns):
        src = n
        for step in range(conns-1):
            id+=1

            dst=(src+step+1)%conns

            out = str(array_nodes[src]) + "->" + str(array_nodes[dst]) + " id " + str(id)

            if (start_after):
                if last:
                    out = out + " start 0 size " + str(int(flowsize/conns))
                else:
                    out = out + " start 0 size " + str(int(flowsize/conns)) + " send_done_trigger " + str(trig_id)
            else:
                if last:
                    out = out + " trigger " + str(trig_id - 1) + " size " + str(int(flowsize/conns))
                else:
                    out = out + " trigger " + str(trig_id - 1) + " size " + str(int(flowsize/conns)) + " send_done_trigger " + str(trig_id)

            lines.append(out)
    trig_id += 1

    return lines, id, trig_id

def main():
    if len(sys.argv) != 5:
        print("Usage: python gen_alltoall_isend.py <filename> <nodes> <conns> <flowsize>")
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

    lines, final_id, final_trig_id = create_connection(conns, flowsize, array_nodes, id, trig_id, True, True)

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

