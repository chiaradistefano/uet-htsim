import os
import re
import matplotlib.pyplot as plt
import numpy as np

# =========================================================
# 1. CONFIGURAZIONE DELLE DIRECTORY E PARAMETRI
# =========================================================
DIR_INC = "results/final_comparison/tmp"
DIR_ALLGATHER = "results/test_allgather/tmp"

SIZES_BYTES = [4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864, 268435456]
LABELS = ["4B", "16B", "64B", "256B", "1KiB", "4KiB", "16KiB", "64KiB", "256KiB", "1MiB", "4MiB", "16MiB", "64MiB", "256MiB"]

# =========================================================
# 2. FUNZIONI DI ESTRAZIONE DATI
# =========================================================
def get_last_finished_time(filepath):
    """Legge il file riga per riga e trova il tempo massimo dell'evento 'finished at'."""
    max_time = 0.0
    pattern = r"finished at ([\d\.]+)"
    
    if not os.path.exists(filepath):
        print(f"   [ATTENZIONE] File non trovato: {filepath}")
        return None
    
    with open(filepath, 'r') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                t = float(match.group(1))
                if t > max_time:
                    max_time = t
    return max_time if max_time > 0 else None

# Liste per salvare i risultati estratti
valid_sizes_bytes = []
valid_labels = []
time_ina_us = []
time_bine_small_us = []
time_bine_large_us = []

print("Estrazione dati dai file di log in corso...")

for label, size_b in zip(LABELS, SIZES_BYTES):
    inc_file = os.path.join(DIR_INC, f"ina_{label}.out")
    bine_small_file = os.path.join(DIR_INC, f"host_{label}.out")
    allgather_file = os.path.join(DIR_ALLGATHER, f"allgather_host_{label}.out")
    
    t_inc = get_last_finished_time(inc_file)
    t_bine_small = get_last_finished_time(bine_small_file)
    t_allgather = get_last_finished_time(allgather_file)
    
    if t_inc is not None and t_bine_small is not None and t_allgather is not None:
        valid_sizes_bytes.append(size_b)
        valid_labels.append(label)
        
        time_ina_us.append(t_inc)
        time_bine_small_us.append(t_bine_small)
        
        # HACK MATEMATICO: All-Reduce (Large) = Reduce-Scatter + All-Gather
        # Pertanto il tempo totale è esattamente il doppio dell'All-Gather
        t_bine_large = t_allgather * 2.0
        time_bine_large_us.append(t_bine_large)
        
        print(f"  [{label}] INA: {t_inc} us | BINE Small: {t_bine_small} us | BINE Large: {t_bine_large} us (Da AG: {t_allgather})")
    else:
        print(f"  [{label}] Dati mancanti, salto...")

# Convertiamo in array numpy
valid_sizes_bytes = np.array(valid_sizes_bytes)
time_ina_us = np.array(time_ina_us)
time_bine_small_us = np.array(time_bine_small_us)
time_bine_large_us = np.array(time_bine_large_us)

# =========================================================
# 3. CALCOLO DELLA LARGHEZZA DI BANDA EFFETTIVA (GOODPUT)
# =========================================================
bits_sent = valid_sizes_bytes * 8

# Banda in Gbps
bw_ina_gbps = (bits_sent / (time_ina_us * 1e-6)) / 1e9
bw_bine_small_gbps = (bits_sent / (time_bine_small_us * 1e-6)) / 1e9
bw_bine_large_gbps = (bits_sent / (time_bine_large_us * 1e-6)) / 1e9

# =========================================================
# 4. GENERAZIONE DEL GRAFICO
# =========================================================
plt.style.use('seaborn-v0_8-whitegrid')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# ---- GRAFICO 1: TEMPO DI COMPLETAMENTO ----
ax1.plot(valid_sizes_bytes, time_bine_small_us / 1000, marker='o', markersize=6, linestyle='-', color='#1f77b4', linewidth=2.5, label='BINE (Small Msg)')
ax1.plot(valid_sizes_bytes, time_bine_large_us / 1000, marker='^', markersize=6, linestyle='-', color='#ff7f0e', linewidth=2.5, label='BINE (Large Msg)')
ax1.plot(valid_sizes_bytes, time_ina_us / 1000, marker='s', markersize=6, linestyle='--', color='#d62728', linewidth=2.5, label='In-Network')

ax1.set_xlabel('Dimensione del Vettore', fontsize=12)
ax1.set_ylabel('Flow Completion Time (us)', fontsize=12)
ax1.set_title('Confronto Tempi di Completamento (FCT)', fontsize=14, fontweight='bold')
ax1.set_xscale('log', base=2) 
ax1.set_yscale('log', base=10) 
ax1.set_xticks(valid_sizes_bytes)
ax1.set_xticklabels(valid_labels, rotation=45, ha='right')
ax1.legend(fontsize=11, loc='upper left')
ax1.grid(True, which="both", ls="--", alpha=0.6)

# ---- GRAFICO 2: LARGHEZZA DI BANDA (GOODPUT) ----
ax2.plot(valid_sizes_bytes, bw_bine_small_gbps, marker='o', markersize=6, linestyle='-', color='#1f77b4', linewidth=2.5, label='BINE (Small Msg)')
ax2.plot(valid_sizes_bytes, bw_bine_large_gbps, marker='^', markersize=6, linestyle='-', color='#ff7f0e', linewidth=2.5, label='BINE (Large Msg)')
ax2.plot(valid_sizes_bytes, bw_ina_gbps, marker='s', markersize=6, linestyle='--', color='#d62728', linewidth=2.5, label='In-Network')

# ---- AGGIUNTA ASINTOTI TEORICI ----
# Asintoto Arancione (50 Gbps)
ax2.axhline(y=50, color='#ff7f0e', linestyle='-.', linewidth=1.5, alpha=0.8, label='Picco Ottimale Host-based (50 Gbps)')
# Asintoto Rosso (100 Gbps)
ax2.axhline(y=100, color='#d62728', linestyle='-.', linewidth=1.5, alpha=0.8, label='Picco Ottimale In-Network (100 Gbps)')

# Modifica principale: tetto alzato a 140 Gbps!
ax2.set_ylim(-2, 140) 
ax2.set_xlabel('Dimensione del Vettore', fontsize=12)
ax2.set_ylabel('Goodput Algoritmico (Gbps)', fontsize=12)
ax2.set_title('Confronto Efficienza di Rete (Goodput)', fontsize=14, fontweight='bold')
ax2.set_xscale('log', base=2)
ax2.set_xticks(valid_sizes_bytes)
ax2.set_xticklabels(valid_labels, rotation=45, ha='right')

# Legenda pulita e solidificata con framealpha
ax2.legend(fontsize=11, loc='upper left', framealpha=0.95)
ax2.grid(True, which="both", ls="--", alpha=0.6)

# =========================================================
# 5. SALVATAGGIO IMMAGINE
# =========================================================
plt.tight_layout()
plt.savefig('grafico_finale_3linee.png', dpi=300, bbox_inches='tight')
print("\nSuccesso! L'immagine è stata generata: 'grafico_finale_3linee.png'")