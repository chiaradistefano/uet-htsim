# Generate a bine reduce-scatter traffic matrix.
# python gen_reducescatter_bine.py <filename> <nodes> <conns> <flowsize> 
# Parameters:
# <nodes>   number of nodes in the topology
# <conns>    number of active connections
# <flowsize>   size of the flows in bytes

import sys
import math

RHOS = [1, -1, 3, -5, 11, -21, 43, -85, 171, -341, 683, -1365, 2731, -5461, 10923, -21845, 43691, -87381, 174763, -349525]
def pi(rank, step, conns):
    if (rank & 1) == 0:
        dst = (rank + RHOS[step]) % conns
    else:
        dst = (rank - RHOS[step]) % conns

    if dst < 0:
        dst += conns

    return dst


def create_connection(conns, flowsize, array_nodes, id, trig_id):

    lines = []
    for n in range(0,conns):
        src=n
        for step in range(int(math.log2(conns))):
            id+=1

            if step!=0:
                src=dst

            dst = pi(src, step, conns)

            out = str(array_nodes[src]) + "->" + str(array_nodes[dst]) + " id " + str(id)

            if step == 0:
                out = out + " start 0"
            else:
                out = out + " trigger " + str(trig_id)
                trig_id += 1

            out = out + " size " + str(int(flowsize/(2**(step+1))))

            if step != int(math.log2(conns))-1:
                out = out + " send_done_trigger " + str(trig_id)
            lines.append(out)

    return lines, id, trig_id

def main():
    if len(sys.argv) != 5:
        print("Usage: python gen_reducescatter_bine.py <filename> <nodes> <conns> <flowsize>")
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

