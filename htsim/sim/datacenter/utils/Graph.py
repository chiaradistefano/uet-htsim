import matplotlib.pyplot as plt
import math

def gen_multi_plot(packet_size, times_list, labels=None):
    """
    Generate a graph with multiple curves on the same Cartesian plane.

    Parameters:
        packet_size (list): packet sizes
        times_list (list of lists): list of execution time series
        labels (list): labels shown in the legend
    """

    # Check that each time vector has the same length
    for time in times_list:
        if len(time) != len(packet_size):
            raise ValueError("Each time list must have the same length as the packet size list.")

    plt.figure(figsize=(10, 6))

    # Default labels
    if labels is None:
        labels = [f"Serie {i+1}" for i in range(len(times_list))]

    # Matplotlib automatically assigns different colors
    for time, label in zip(times_list, labels):
        plt.plot(packet_size, time, marker='o', label=label)

    plt.title("Plot AllGather Bruck")
    plt.xlabel("Vector Size")
    plt.ylabel("Time (ms)")
    plt.grid(True)

    plt.xscale("log", base=2)  

    labels_readable = [human_readable_size(x) for x in packet_size]
    plt.xticks(packet_size, labels_readable, rotation=45)  

    # Legend
    plt.legend(loc='upper left')

    plt.subplots_adjust(bottom=0.22)

    # Save the graph
    plt.savefig("multi_plot.png")
    print("Graph saved as multi_plot.png")


def human_readable_size(size_bytes):
    """Convert a byte value into a human-readable format (KiB, MiB, GiB)."""
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    power = int(math.log(size_bytes, 1024))
    power = min(power, len(units) - 1)
    value = size_bytes / (1024 ** power)

    if value.is_integer():
        value = int(value)
    else:
        value = round(value, 2)

    return f"{value} {units[power]}"


# ------------------------
# Example usage
# ------------------------
if __name__ == "__main__":
    packet_size = [4 , 32 , 256 , 2*1024 , 16*1024 , 128*1024 , 1*1024*1024 , 8*1024*1024 , 64*1024*1024 , 512*1024*1024]

    time1 = [0.0, 0.0, 671.51, 671.889, 675.05, 699.36, 827.642, 1440.57, 6198.85, 44214.7] 
    time2 = [0.0, 0.0, 479.628, 479.802, 481.218, 492.644, 602.679, 1207.75, 6445.98, 49133.7]
    time3 = [0.0, 0.0, 540.569, 540.631, 541.121, 545.046, 631.468, 1225.81, 5969.1, 43981.0]
    time4 = [0.0, 0.0, 524.45, 524.498, 524.886, 527.986, 612.093, 1205.6, 5949.22, 43960.6]
    time5 = [0.0, 0.0, 542.168, 542.402, 544.27, 559.215, 611.631, 727.716, 5617.95, 44567.6]

    gen_multi_plot(
        packet_size,
        [time1, time2, time3, time4, time5],
        labels=["Fat Tree", "Multi Gpu", "Scale Up 32 Porte", "Scale Up 64 Porte", "Scale Up Multi Planes"]
    )
