
from network import collect_network_data
from analysis.analyzer import analyze_trace

destination = input("Enter destination (e.g. google.com): ")

print("\nCollecting network data... Please wait.")

trace_data = collect_network_data(destination)
results = analyze_trace(trace_data)

print("\n===== PACKET JOURNEY ANALYSIS =====")
print("Destination:", trace_data["destination"])
print("Resolved IP:", trace_data["resolved_ip"])

print("\n===== ANALYSIS RESULTS =====")
for metric, value in results.items():
    print(f"{metric}: {value}")