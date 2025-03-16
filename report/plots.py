import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../measurements/meas_times_aws_from_inside_finger.csv")

df["throughput_bench1"] = 500 / df["time_bench1"]
df["throughput_bench2"] = 500 / df["time_bench2"]

plt.figure(figsize=(8, 5))
for model in df["consistency_model"].unique():
    subset = df[df["consistency_model"] == model]
    plt.plot(subset["replication_factor"], subset["throughput_bench1"], marker='o', label=model)

plt.xticks([1, 3, 5, 8, 10])
plt.xlabel("Number of Copies")
plt.ylabel("Throughput (ops)")
plt.title("Insertions (with finger table)")
plt.legend()
plt.savefig("insertions_finger.pdf")

plt.figure(figsize=(8, 5))
for model in df["consistency_model"].unique():
    subset = df[df["consistency_model"] == model]
    plt.plot(subset["replication_factor"], subset["throughput_bench2"], marker='o', label=model)

plt.xticks([1, 3, 5, 8, 10])
plt.xlabel("Number of Copies")
plt.ylabel("Throughput (ops)")
plt.title("Queries (with finger table)")
plt.legend()
plt.savefig("queries_finger.pdf")
