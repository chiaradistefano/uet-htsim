#!/usr/bin/env python

# Generate an incast traffic matrix.
# python gen_incast.py <filename> <nodes> <conns> <flowsize> <extrastarttime> <randseed> <prefer_remote>

import os
import sys
from random import seed, shuffle, randint, choice


def create_connection(conns, flowsize, array_nodes, id, trig_id, extrastarttime, randseed, prefer_remote, start, last, dst_nodes):
    
    lines = []

    if randseed != 0:
        seed(randseed)

    dst = dst_nodes

    srcs = []
    if prefer_remote == 0:
        srcs = [n for n in array_nodes if n != dst]
    else:
        half = len(array_nodes) // 2
        srcs = [n for n in array_nodes[half:] if n != dst]

    shuffle(srcs)

    for n in range(conns - 1):
        id += 1
        extra = randint(0, int(extrastarttime * 1000000))
        if (start):
            if last:
                out = str(srcs[n]) + "->" + str(dst) + " id " + str(id) + " start " + str(extra) + " size " + str(flowsize)
            else:
                out = str(srcs[n]) + "->" + str(dst) + " id " + str(id) + " start " + str(extra) + " size " + str(flowsize) + " send_done_trigger " + str(trig_id)
        else: 
            if last:
                out = str(srcs[n]) + "->" + str(dst) + " id " + str(id) + " trigger " + str(trig_id - 1) + " size " + str(flowsize)
            else:
                out = str(srcs[n]) + "->" + str(dst) + " id " + str(id) + " trigger " + str(trig_id - 1) + " size " + str(flowsize) + " send_done_trigger " + str(trig_id)
        lines.append(out)
    trig_id += 1

    return lines, id, trig_id


def main():
    if len(sys.argv) != 8:
        print("Usage: python gen_incast.py <filename> <nodes> <conns> <flowsize> <extrastarttime> <randseed> <prefer_remote>")
        sys.exit()

    filename = sys.argv[1]
    nodes = int(sys.argv[2])
    conns = int(sys.argv[3])
    flowsize = int(sys.argv[4])
    extrastarttime = float(sys.argv[5])
    randseed = int(sys.argv[6])
    prefer_remote = int(sys.argv[7])

    print("Nodes: ", nodes)
    print("Connections: ", conns)
    print("Flowsize: ", flowsize, "bytes")
    print("ExtraStartTime: ", extrastarttime, "us")
    print("Random Seed ", randseed)

    array_nodes = list(range(nodes))
    id = 0
    trig_id = 1

    lines, _, _ = create_connection(conns, flowsize, array_nodes, id, trig_id, extrastarttime, randseed, prefer_remote, True, True, 0)

    num_flows = len(lines)

    with open(filename, "w") as f:
        print("Nodes", nodes, file=f)
        print("Connections", num_flows, file=f)
        for line in lines:
            print(line, file=f)


if __name__ == "__main__":
    main()