# Packet Logging

Provides packet-level telemetry for simulations using the `-log packet` flag. It records every packet departure event across the network topology, so the output file can grow extremely large during long simulations. This enable precise post-simulation analysis. 

## How to Run

To enable packet logging, append the `-log packet` flag to your simulation execution command:

```bash
./htsim_uec -log packet [other_args...]
```

## Log File Format 

The generated log file is a headerless CSV that captures information about the name of the port, the time of the simulation in microseconds, the packet size, and the duration of the transmission in picoseconds.

```bash
SRC1->LF0,0.325120,4064,325120
LF10->DST42,18.104320,64,5120
SP2->SP6(0),18.369920,64,5120
```

# Fat Tree topologies with different Scale Up networks — How to Run Simulations

The classic Fat-Tree topology is extended with a scale-up network in three implementations. Each has its own binary:

| Binary | Implementation |
|--------|---------------|
| `htsim_uec_mg` | Multi-GPU |
| `htsim_uec_sh` | Based on the use of dedicated high-performance switches |
| `htsim_uec_sh_mp` | Previous implementation but designed using the Multi-Rail Switching concept |

## Running a Simulation

```bash
./htsim_uec_sh_mp -topo topologies/fat_tree_test_sh.topo \
    -tm connection_matrices/allgather_ring/allgather1MiB.cm \
    -end 10000000
```

Replace the binary with `htsim_uec_mg` or `htsim_uec_sh` as needed. 

# In-Network AllReduce (INA) — How to Run Simulations
 
The INA implementation extends the Fat-Tree topology to support in-network all-reduce. It uses a dedicated binary `htsim_inc_uec` and a **special connection matrix format** that differs from all others.
 
## Prerequisites
 
Simulations require:
 
- An **INA connection matrix file** — generated with `gen_allreduce_ina.py` (see below)

## Connection Matrix Format

The key difference is that INA flows use `#` as the destination placeholder instead of a numeric host ID. This tells the simulator to route the flow to the in-network aggregation switch rather than a specific endpoint, triggering `UecIncSrc` and registering the sender as a participant in the in-network AllReduce job.
 
Normal (non-INA) flows with a numeric destination can coexist in the same file.
 
## Running a Simulation
 
```bash
./htsim_inc_uec -tm connection_matrices/allreduce_ina/allreduce1MiB.cm \
    -end 10000000 -sender_cc_only
```
