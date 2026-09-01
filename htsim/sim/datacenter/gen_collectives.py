import random
import math
import importlib


def gen_array(percA: float, percB: float, type: str, nodes: int, conns: int):

    if not math.isclose(percA + percB, 1.0, abs_tol=1e-9):
        raise ValueError(
            f"percA ({percA}) + percB ({percB}) "
            f"must be equal to 1."
        )
    if percA < 0 or percA > 1:
        raise ValueError("percA must be between 0 and 1.")
    if nodes < 0:
        raise ValueError("nodes need to be a positive number.")
    if conns < 0:
        raise ValueError("conns deve essere un intero non negativo.")
    type = type.lower().strip()
    if type not in ("linear", "interleaved", "random"):
        raise ValueError(
            f"type '{type}' unkown . Choose: linear, interleaved, random."
        )

    target_A = nodes * percA

    if target_A <= 1:
        nodesA = 1 
    else:
        esp_inf = math.floor(math.log2(target_A))
        esp_sup = math.ceil(math.log2(target_A))
        
        potenza_inf = 2 ** esp_inf
        potenza_sup = 2 ** esp_sup
        
        # use the nearest power of two
        if (target_A - potenza_inf) < (potenza_sup - target_A):
            nodesA = potenza_inf
        else:
            nodesA = potenza_sup

    # we ensure that nodes = nodesA + nodesB
    nodesB = nodes - nodesA

    allNodes = list(range(nodes))

    if type == "linear":
        # First nodes to A, others to B
        arrayA = allNodes[:nodesA]
        arrayB = allNodes[nodesA:]

    elif type == "interleaved":
        # A, B, A, B, ...
        even = allNodes[0::2]
        arrayA = even[:nodesA]

        last_even = even[nodesA:]
        odd = allNodes[1::2]
        arrayB = odd + last_even

    elif type == "random":
        # Random distribution
        shuffled = allNodes[:]
        random.shuffle(shuffled)
        arrayA = shuffled[:nodesA]
        arrayB = shuffled[nodesA:]

    arrayA.sort()
    arrayB.sort()
    return arrayA, arrayB


def gen_coll_incast(collA: str, collB: str, nodes: int, conns: int, size: int,
                     filename: str, num: int, arrayA: list, arrayB: list, sendTo: int):
    to_write = []
    module = importlib.import_module(f"connection_matrices.gen_{collA}")
    lines, new_id, new_trig_id = module.create_connection(conns=len(arrayA),flowsize=size,array_nodes=arrayA,id=0,trig_id=1,)

    module2 = importlib.import_module(f"connection_matrices.gen_{collB}")

    to_write = lines 

    trigger = new_trig_id
    for t in range(0, num):
        if t == 0 and t != num - 1:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, 0, 0, 0, True, False, sendTo)
        elif t == 0 and t == num - 1:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, 0, 0, 0, True, True, sendTo)
        elif t == num - 1:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, 0, 0, 0, False, True, sendTo)
        else:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, 0, 0, 0, False, False, sendTo)
        to_write = to_write + lines1
        new_id = id1
        new_trig_id = trig_id1

    num_flows = len(to_write)
    end_trigger = trigger + num - 1

    for t in range(1, trigger):
        out = "trigger id " + str(t) + " oneshot"
        to_write.append(out)

    if trigger < end_trigger:
        for t in range(trigger, end_trigger):
            out = "trigger id " + str(t) + " barrier count " + str(len(arrayB) - 1)
            to_write.append(out)
    else:
        end_trigger = trigger

    with open(filename, "w") as f:
        print(f"Nodes", nodes, file=f)
        print(f"Connections", num_flows, file=f) 
        print(f"Triggers", end_trigger - 1, file=f)  
        
        for line in to_write:
            print(line, file=f)
    return sendTo

def gen_coll_alltoall(collA: str,collB: str,nodes: int,conns: int,size: int,filename: str,num: int, arrayA: list, arrayB: list):
    to_write = []
    modulo = importlib.import_module(f"connection_matrices.gen_{collA}")
    lines, new_id, new_trig_id = modulo.create_connection(conns=len(arrayA),flowsize=size,array_nodes=arrayA,id=0,trig_id=1,)

    module2 = importlib.import_module(f"connection_matrices.gen_{collB}")

    to_write = lines 

    trigger = new_trig_id
    for t in range(0, num):
        if t == 0 and t != num - 1:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, True, False)
        elif t == 0 and t == num - 1:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, True, True)
        elif t == num - 1:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, False, True)
        else:
            lines1, id1, trig_id1 = module2.create_connection(len(arrayB), 131072, arrayB, new_id, new_trig_id, False, False)
        to_write = to_write + lines1
        new_id = id1
        new_trig_id = trig_id1

    num_flows = len(to_write)
    end_trigger = trigger + num - 1

    for t in range(1, trigger):
        out = "trigger id " + str(t) + " oneshot"
        to_write.append(out)

    if trigger < end_trigger:
        for t in range(trigger, end_trigger):
            out = "trigger id " + str(t) + " barrier count " + str(len(arrayB)*(len(arrayB) - 1))
            to_write.append(out)
    else:
        end_trigger = trigger

    with open(filename, "w") as f:
        print(f"Nodes", nodes, file=f)
        print(f"Connections", num_flows, file=f) 
        print(f"Triggers", end_trigger - 1, file=f)  
        
        for line in to_write:
            print(line, file=f)
    return 0


if __name__ == "__main__":

    arA, arB = gen_array(0.20, 0.80, "linear", 20, 20)

    gen_coll_incast("allgather_bine", "incast", 20, 20, 1024, "incast.cm", 0, arA, arB, 17)
