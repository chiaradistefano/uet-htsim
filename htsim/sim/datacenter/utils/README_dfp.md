# Dragonfly+ Topology — Simulation Guide

## 1. Overview

The **Dragonfly+** topology is a network architecture where switches are organized into **groups**. It features a bipartite structure at the intra-group level and a fully connected network at the inter-group level. Within each group, **leaf switches** are connected to hosts and to the spine switches in the same group, while **spine switches** are connected to spine switches in other groups and to leaf switches in the same group.

### 1.1 Structural Parameters

The topology is fully determined by four structural parameters:

| Symbol | Flag | Meaning |
|--------|----------|---------|
| `p` | `-p` | Number of **host ports** per leaf switch. |
| `s` | `-s` | Number of **spine switches** per leaf switch, equal to the number of spine per group by construction. |
| `l` | `-l` | Number of **leaf switches** per spine switch, equal to the number of leaf per group by construction. |
| `h` | `-h` | Number of **global links** per spine switch (links going out to other groups). |
| `k` | *(derived)* | Router radix `k = s + p = h + l`. |
| `a` | *(derived)* | Total switches per group: `a = s + l`. |

> **Load-balance:** the parameters `p`, `s`, `l`, `h` must either all be set or none of them set. If none are set, the simulator automatically derives them as `p = s = l = h = k/2` (perfectly balanced traffic configuration), selecting the smallest `k` that satisfies the number of requested nodes.

### 1.2 Topology Size Variants

The number of groups and total hosts depend on the topology size variant selected via ``-size s\|m\|l``.

| Variant | Groups | Max hosts | Meaning |
|---------|--------|-----------|---------|
| `LARGE` | `s × h + 1` | `l × p × (s × h + 1)` | Each **group** is connected to every other group by a single link. |
| `MEDIUM` | `h + 1` | `l × p × (h + 1)` | Each **spine** is connected to every other group by a single link. |
| `SMALL` | `h / no_par_link + 1` | `l × p × (h / no_par_link + 1)` | Each **spine** is connected to every other group by `no_par_link` parallel links. |

---

## 2. Building the project

There are two separate binaries for Fat-Tree and Dragonfly+ experiments:

| Binary | Description |
|--------|-------------|
| `htsim_roce_ft` | Standard Fat-Tree RoCE simulation. |
| `htsim_roce_dfp` | Dragonfly+ RoCE simulation. |

Install the Python requirements by running:

```bash
pip install -r requirements.txt
```

Then compile the project from the `sim/` folder by running

```bash
cmake -S . -B build # To configure the cmake project
cmake --build build --parallel --target htsim_roce_dfp # To build the project with Dragonfly+
```

---

## 3. Command-Line Parameters

### 3.1 Topology Parameters

| Flag | Description |
|------|-------------|
| `-nodes N` | Total number of host nodes to simulate, default 432. |
| `-size s\|m\|l` | Topology size variant, default is large. |
| `-s X` | Spine switches per leaf, optional parameter. |
| `-l X` | Leaf switches per spine, optional parameter. |
| `-h X` | Global links per spine, optional parameter. |
| `-p X` | Host ports per leaf, optional parameter. |
| `-p_link N` | Number of parallel links between each pair of spine switches. Only valid for `-size s` and this value must be chosen as a divisor of h. |
| `-threshold T` | Queue-size threshold used by the FPAR routing algorithm. Defaults to `queue_size / 2`. |
| `-topo FILE` | Path to a topology configuration file. When supplied, all topology parameters come from the file and topology flags are ignored. |

> ⚠️ `-nodes` must be specified. The topology is then generated based on the chosen or default configuration, ensuring that the total node count is greater than or equal to the requested number.

### 3.2 Routing Strategy (`-strat`)

> ⚠️ `-strat` must always be specified.

Two routing strategies are supported for Dragonfly+:

| Value | Description |
|-------|-------------|
| `minimal` | Packets always follow the shortest path. |
| `fpar` | **Fully Progressive Adaptive Routing (FPAR):** paths are classified into HIGH PRIORITY(minimal path), MEDIUM PRIORITY (use one intermediate spine), and LOW PRIORITY (use an interemediate group). Based on these priorities, the switch selects the egress port with the smallest queue size below a given threshold `T`. |

---

## 4. Running Simulations

### 4.1 Simple example

Minimal routing, traffic read from a file:

```bash
./htsim_roce_dfp -tm connection_matrices/one.cm -nodes 16 -strat minimal 
```

### 4.2 Explicit Dragonfly+ Parameters

Medium topology, 5 groups, 80 hosts:

```bash
./htsim_roce_dfp -nodes 80 -size m -s 4 -l 4 -h 4 -p 4  \
                  -strat fpar -tm traffic.cm
```

### 4.3 Small Topology with Parallel Links

Small topology, 2 parallel inter-group links, 3 groups, 48 nodes:

```bash
./htsim_roce_dfp -nodes 48 -size s -s 4 -l 4 -h 4 -p 4 -p_link 2 \
                  -strat minimal -tm traffic.cm
```

Small topology, 4 parallel inter-group links, 2 groups, 32 nodes:

```bash
./htsim_roce_dfp -nodes 32 -size s -p_link 4 \
                  -strat fpar -tm traffic.cm
```

### 4.4 Using a Topology File

Load topology from a configuration file:

```bash
./htsim_roce_dfp -topo my_topo.cfg -strat fpar \
                  -end 5000 -tm traffic.txt
```

---

## 5. Validation Rules & Common Errors

The simulator enforces the following constraints at startup and exits with a descriptive message if any are violated:
 
- `s + p == h + l` (equal radix)
- The parameters `s`, `l`, `h`, `p` must either all be set or none at all.
- `h % no_par_link == 0` for SMALL topology
- When setting the `s`, `l`, `h`, `p` parameters, need to verify whether that specific configuration can support the requested number of nodes
- `-p_link > 1` only valid for SMALL topology
- `-strat` must be set
- `-nodes` must match `N` in the traffic matrix

---
