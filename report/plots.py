import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../cli/meas_aws_from_inside.csv")

df["throughput_bench1"] = 500 / df["time_bench1"]
df["throughput_bench2"] = 500 / df["time_bench2"]

plt.figure(figsize=(8, 5))
for model in df["consistency_model"].unique():
    subset = df[df["consistency_model"] == model]
    plt.plot(subset["replication_factor"], subset["throughput_bench1"], marker='o', label=model)

plt.xticks([1, 3, 5])
plt.xlabel("Number of Copies")
plt.ylabel("Throughput (ops)")
plt.title("Insertions")
plt.legend()
plt.savefig("insertions.png")

plt.figure(figsize=(8, 5))
for model in df["consistency_model"].unique():
    subset = df[df["consistency_model"] == model]
    plt.plot(subset["replication_factor"], subset["throughput_bench2"], marker='o', label=model)

plt.xticks([1, 3, 5])
plt.xlabel("Number of Copies")
plt.ylabel("Throughput (ops)")
plt.title("Queries")
plt.legend()
plt.savefig("queries.png")
